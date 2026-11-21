"""Serveur HTTP local préparé pour la synchronisation de Repère.

C'est un adaptateur PILOTANT : un appareil distant commande l'application à travers lui (c'est pourquoi il
vit dans `adapters/driving/` et non dans `adapters/driven/`).
Il expose un état de santé (/health), le QR code (/qr.png), une page de test (/) et un WebSocket (/ws) qui
transporte les messages de synchronisation (voir sync_protocol.py). Le WebSocket exige le JETON D'APPAIRAGE,
contenu dans l'adresse du QR code : sans lui (403), personne sur le réseau ne peut lire ni écrire de données.
Le trafic n'est pas chiffré (ws://) : à n'utiliser que sur un réseau Wi-Fi de confiance.

Le serveur tourne dans des threads : il ne touche jamais à l'application. Il dépose ses événements dans une
file que l'interface vide avec `poll()` dans son propre thread ; elle répond avec `send()`.
"""
from __future__ import annotations

import hmac
import io
import itertools
import json
import queue
import secrets
import socket
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .sync_page import PAGE
from .websocket import WebSocketConnection, upgrade

MAX_CLIENTS = 8   # appareils connectés en même temps


def lan_address() -> str:
    """Retourne l'adresse IPv4 utile sur le réseau local, sans ouvrir de connexion distante."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


@dataclass(frozen=True)
class SyncEvent:
    """Ce qui s'est passé côté réseau : kind = « connected », « disconnected » ou « message » (avec `text`)."""
    kind: str
    client: int
    address: str
    text: str = ""


class SyncHTTPServer:
    """Serveur léger qui tourne dans un thread séparé de l'interface graphique."""

    def __init__(self, port: int = 8765):
        if not 1 <= port <= 65535:
            raise ValueError("Le port doit être compris entre 1 et 65535.")
        self.port = port
        self.token = secrets.token_urlsafe(16)   # jeton d'appairage : nouveau à chaque instance du serveur
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._events: queue.SimpleQueue = queue.SimpleQueue()
        self._clients: dict[int, tuple[WebSocketConnection, str]] = {}
        self._clients_lock = threading.Lock()
        self._ids = itertools.count(1)

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def base_url(self) -> str:
        return f"http://{lan_address()}:{self.port}"

    @property
    def pairing_url(self) -> str:
        """Adresse du QR code : l'adresse du serveur + le jeton qui autorise le WebSocket."""
        return f"{self.base_url}/?token={self.token}"

    @property
    def client_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    def start(self) -> str:
        if self.running:
            return self.base_url

        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _headers(self, content_type: str, length: int, status: int = 200) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

            def _serve_websocket(self) -> None:
                given = (parse_qs(urlsplit(self.path).query).get("token") or [""])[0]
                if not hmac.compare_digest(given.encode("utf-8"), owner.token.encode("utf-8")):
                    self.send_error(403, "Jeton d'appairage invalide")
                    return
                if owner.client_count >= MAX_CLIENTS:
                    self.send_error(503, "Trop d'appareils connectés")
                    return
                connection = upgrade(self)
                if connection is None:
                    return
                address = self.client_address[0]
                client = owner._register(connection, address)
                try:
                    while (text := connection.receive()) is not None:
                        owner._events.put(SyncEvent("message", client, address, text))
                finally:
                    owner._unregister(client)
                    connection.close()    # envoie la trame de fermeture éventuelle...
                    connection.join()     # ...et attend qu'elle soit partie avant que la socket soit rendue

            def do_GET(self) -> None:
                path = urlsplit(self.path).path
                if path == "/ws":
                    self._serve_websocket()
                elif path == "/health":
                    payload = json.dumps({"status": "ok", "service": "repere-sync"}, ensure_ascii=False).encode()
                    self._headers("application/json; charset=utf-8", len(payload))
                    self.wfile.write(payload)
                elif path == "/qr.png":
                    try:
                        png = owner.qr_png()
                    except RuntimeError as exc:   # dépendance 'qrcode' absente : réponse HTTP claire, pas de socket coupée
                        message = str(exc).encode("utf-8")
                        self._headers("text/plain; charset=utf-8", len(message), status=501)
                        self.wfile.write(message)
                        return
                    self._headers("image/png", len(png))
                    self.wfile.write(png)
                else:
                    html = PAGE.encode("utf-8")
                    self._headers("text/html; charset=utf-8", len(html))
                    self.wfile.write(html)

            def log_message(self, format: str, *args) -> None:
                return

        self._server = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="repere-sync-server", daemon=True)
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        if self._server is None:
            return
        with self._clients_lock:
            connections = [connection for connection, _address in self._clients.values()]
        for connection in connections:   # sinon leurs threads resteraient bloqués en lecture
            connection.abort()
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    # ---- échange avec l'interface (appelé depuis SON thread) ------------------------------------------------
    def poll(self) -> list[SyncEvent]:
        """Les événements arrivés depuis le dernier appel (ne bloque jamais)."""
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def send(self, text: str, client: int | None = None) -> int:
        """Envoie un message à un appareil (ou à tous si `client` est None) ; retourne le nombre d'appareils atteints."""
        with self._clients_lock:
            targets = [c for number, (c, _a) in self._clients.items() if client is None or number == client]
        return sum(1 for connection in targets if connection.send_text(text))

    def _register(self, connection: WebSocketConnection, address: str) -> int:
        with self._clients_lock:
            client = next(self._ids)
            self._clients[client] = (connection, address)
        self._events.put(SyncEvent("connected", client, address))
        return client

    def _unregister(self, client: int) -> None:
        with self._clients_lock:
            entry = self._clients.pop(client, None)
        if entry is not None:
            self._events.put(SyncEvent("disconnected", client, entry[1]))

    def qr_png(self) -> bytes:
        """Génère un QR code contenant l'adresse d'appairage (serveur + jeton)."""
        try:
            import qrcode
        except ImportError as exc:
            raise RuntimeError("Installez la dépendance 'qrcode' (pip install qrcode[pil]).") from exc

        image = qrcode.make(self.pairing_url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
