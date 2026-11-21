"""WebSocket minimal côté SERVEUR (RFC 6455), en bibliothèque standard uniquement.

Il sert à la synchronisation : messages TEXTE (JSON) dans les deux sens. Pris en charge : poignée de main,
messages fragmentés, ping/pong, fermeture propre. Refusés : trames non masquées (côté client), messages
binaires, messages de plus de `MAX_MESSAGE` octets.

Toutes les ÉCRITURES passent par un thread dédié (file d'attente) : l'appelant (par exemple l'interface
graphique) n'est jamais bloqué par un appareil lent. La lecture se fait dans le thread de la requête HTTP.
"""
from __future__ import annotations

import base64
import hashlib
import queue
import socket
import struct
import threading
from typing import Optional

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_MESSAGE = 8 * 1024 * 1024   # octets : au-delà, la connexion est fermée (code 1009)

OP_CONTINUATION, OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA


class ProtocolError(Exception):
    """Violation du protocole par le client : la connexion est fermée avec ce code."""

    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code, self.reason = code, reason


def accept_key(client_key: str) -> str:
    return base64.b64encode(hashlib.sha1((client_key + GUID).encode("ascii")).digest()).decode("ascii")


def apply_mask(data: bytes, mask: bytes) -> bytes:
    """XOR avec la clé de 4 octets (même opération pour masquer et démasquer)."""
    if not data:
        return b""
    key = (mask * (len(data) // 4 + 1))[:len(data)]
    return (int.from_bytes(data, "big") ^ int.from_bytes(key, "big")).to_bytes(len(data), "big")


def encode_frame(opcode: int, payload: bytes = b"", mask: Optional[bytes] = None) -> bytes:
    """Une trame complète (FIN = 1). `mask` : 4 octets, réservé aux clients (utile surtout pour les tests)."""
    flag = 0x80 if mask else 0
    size = len(payload)
    if size < 126:
        header = bytes([0x80 | opcode, flag | size])
    elif size < 65536:
        header = bytes([0x80 | opcode, flag | 126]) + struct.pack(">H", size)
    else:
        header = bytes([0x80 | opcode, flag | 127]) + struct.pack(">Q", size)
    return header + (mask + apply_mask(payload, mask) if mask else payload)


def close_frame(code: int, reason: str = "") -> bytes:
    return encode_frame(OP_CLOSE, struct.pack(">H", code) + reason.encode("utf-8")[:120])


def upgrade(handler) -> Optional["WebSocketConnection"]:
    """Termine la poignée de main d'un `BaseHTTPRequestHandler`. Répond 400 et retourne None si elle est invalide."""
    headers = handler.headers
    key = headers.get("Sec-WebSocket-Key", "").strip()
    valid = ("websocket" in headers.get("Upgrade", "").lower()
             and "upgrade" in headers.get("Connection", "").lower()
             and headers.get("Sec-WebSocket-Version", "").strip() == "13" and key)
    if not valid:
        handler.send_error(400, "Requête WebSocket invalide")
        return None
    handler.wfile.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                         f"Sec-WebSocket-Accept: {accept_key(key)}\r\n\r\n").encode("ascii"))
    return WebSocketConnection(handler.connection, handler.rfile, handler.wfile)


class WebSocketConnection:
    def __init__(self, sock: socket.socket, rfile, wfile):
        self._sock, self._rfile, self._wfile = sock, rfile, wfile
        self._outbox: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._closing = False
        self._writer = threading.Thread(target=self._write_loop, name="repere-ws-writer", daemon=True)
        self._writer.start()

    # ---- envoi (jamais bloquant) -----------------------------------------------------------------
    def send_text(self, text: str) -> bool:
        """Met le message en file d'attente ; False si la connexion se ferme ou est fermée."""
        return self._enqueue(encode_frame(OP_TEXT, text.encode("utf-8")))

    def _enqueue(self, frame: bytes) -> bool:
        with self._lock:
            if self._closing:
                return False
            self._outbox.put(frame)
            return True

    def _write_loop(self) -> None:
        while True:
            frame = self._outbox.get()
            if frame is None:
                break
            try:
                self._wfile.write(frame)
            except OSError:
                break
        self.abort()

    # ---- fermeture ---------------------------------------------------------------------------------
    def close(self, code: int = 1000, reason: str = "") -> None:
        """Fermeture propre : les messages déjà en file partent d'abord, puis la trame de fermeture."""
        with self._lock:
            if self._closing:
                return
            self._closing = True
            self._outbox.put(close_frame(code, reason))
            self._outbox.put(None)

    def abort(self) -> None:
        """Coupe immédiatement (réveille aussi la lecture bloquée). Sans danger si déjà fermée."""
        with self._lock:
            if not self._closing:
                self._closing = True
                self._outbox.put(None)   # réveille le thread d'écriture pour qu'il se termine
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def join(self, timeout: float = 2.0) -> None:
        """Attend que les messages en file soient écrits (à appeler après `close`, avant de rendre la socket)."""
        self._writer.join(timeout)

    # ---- réception ---------------------------------------------------------------------------------
    def receive(self) -> Optional[str]:
        """Prochain message texte, ou None quand la connexion est terminée (fermeture, erreur, violation)."""
        try:
            return self._receive_message()
        except ProtocolError as error:
            self.close(error.code, error.reason)
        except (OSError, EOFError):
            self.abort()
        return None

    def _read(self, count: int) -> bytes:
        data = self._rfile.read(count)
        if len(data) != count:
            raise EOFError
        return data

    def _read_frame(self) -> tuple[bool, int, bytes]:
        first, second = self._read(2)
        if first & 0x70:
            raise ProtocolError(1002, "bits réservés utilisés")
        if not second & 0x80:
            raise ProtocolError(1002, "trame client non masquée")
        length = second & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._read(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._read(8))[0]
        if length > MAX_MESSAGE:
            raise ProtocolError(1009, "message trop volumineux")
        mask = self._read(4)
        return bool(first & 0x80), first & 0x0F, apply_mask(self._read(length), mask)

    def _receive_message(self) -> Optional[str]:
        fragments: list[bytes] = []
        started, total = False, 0
        while True:
            final, opcode, payload = self._read_frame()
            if opcode >= 0x8:   # trames de contrôle : jamais fragmentées, 125 octets au plus
                if not final or len(payload) > 125:
                    raise ProtocolError(1002, "trame de contrôle invalide")
                if opcode == OP_PING:
                    self._enqueue(encode_frame(OP_PONG, payload))
                elif opcode == OP_CLOSE:
                    self.close()
                    return None
                elif opcode != OP_PONG:
                    raise ProtocolError(1002, "opcode inconnu")
                continue
            if opcode == OP_CONTINUATION:
                if not started:
                    raise ProtocolError(1002, "suite de message inattendue")
            elif started:
                raise ProtocolError(1002, "nouveau message avant la fin du précédent")
            elif opcode == OP_BINARY:
                raise ProtocolError(1003, "messages binaires non pris en charge")
            elif opcode != OP_TEXT:
                raise ProtocolError(1002, "opcode inconnu")
            started = True
            total += len(payload)
            if total > MAX_MESSAGE:
                raise ProtocolError(1009, "message trop volumineux")
            fragments.append(payload)
            if final:
                try:
                    return b"".join(fragments).decode("utf-8")
                except UnicodeDecodeError:
                    raise ProtocolError(1007, "texte UTF-8 invalide") from None
