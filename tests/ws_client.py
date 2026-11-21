"""Petit client WebSocket de TEST (octets bruts) : permet de provoquer aussi les violations du protocole."""
import base64
import os
import select
import socket
import struct

from suivi.adapters.driving.websocket import OP_TEXT, apply_mask


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class WsClient:
    def __init__(self, port: int, token: str):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=3)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /ws?token={token} HTTP/1.1\r\nHost: test\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        self._buffer = b""
        while b"\r\n\r\n" not in self._buffer:                  # réponse HTTP : ligne d'état + en-têtes
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            self._buffer += chunk
        head, _, self._buffer = self._buffer.partition(b"\r\n\r\n")
        self.status = int(head.split(b" ")[1])

    def _take(self, count: int):
        """`count` octets (bloque au plus 3 s) ; None si le serveur a coupé la connexion."""
        while len(self._buffer) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                return None
            self._buffer += chunk
        data, self._buffer = self._buffer[:count], self._buffer[count:]
        return data

    def has_data(self, timeout: float = 0.0) -> bool:
        """Un message (ou la fin de flux) est-il déjà arrivé ? Ne bloque pas au-delà de `timeout`."""
        return bool(self._buffer) or bool(select.select([self.sock], [], [], timeout)[0])

    def send_frame(self, opcode: int, payload: bytes = b"", final: bool = True, masked: bool = True,
                   declared_length=None) -> None:
        size = len(payload) if declared_length is None else declared_length
        header = bytes([(0x80 if final else 0) | opcode])
        flag = 0x80 if masked else 0
        if size < 126:
            header += bytes([flag | size])
        elif size < 65536:
            header += bytes([flag | 126]) + struct.pack(">H", size)
        else:
            header += bytes([flag | 127]) + struct.pack(">Q", size)
        mask = os.urandom(4)
        body = mask + apply_mask(payload, mask) if masked else payload
        self.sock.sendall(header + body)

    def send_text(self, text: str) -> None:
        self.send_frame(OP_TEXT, text.encode("utf-8"))

    def recv_frame(self):
        """(opcode, payload) ou None si le serveur a coupé la connexion."""
        head = self._take(2)
        if head is None:
            return None
        length = head[1] & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._take(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._take(8))[0]
        payload = self._take(length) if length else b""
        return None if payload is None else (head[0] & 0x0F, payload)

    def recv_text(self) -> str:
        opcode, payload = self.recv_frame()
        assert opcode == OP_TEXT, opcode
        return payload.decode("utf-8")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
