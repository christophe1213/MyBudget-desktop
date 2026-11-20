"""Serveur HTTP local préparé pour la synchronisation de Repère.

C'est un adaptateur PILOTANT : un appareil distant commande l'application à travers lui (c'est pourquoi il
vit dans `adapters/driving/` et non dans `adapters/driven/`).
Cette première version expose uniquement un état de santé et une page de test.
Elle ne reçoit ni n'envoie encore les données financières.
"""
from __future__ import annotations

import io
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


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


class SyncHTTPServer:
    """Serveur léger qui tourne dans un thread séparé de l'interface graphique."""

    def __init__(self, port: int = 8765):
        if not 1 <= port <= 65535:
            raise ValueError("Le port doit être compris entre 1 et 65535.")
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def base_url(self) -> str:
        return f"http://{lan_address()}:{self.port}"

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

            def do_GET(self) -> None:
                path = urlsplit(self.path).path
                if path == "/health":
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
                    html = (
                        "<!doctype html><meta charset=utf-8><title>Repère synchronisation</title>"
                        "<h1>Repère synchronisation</h1>"
                        "<p>Serveur actif. L'échange de données n'est pas encore implémenté.</p>"
                        '<p><a href="/health">Vérifier l’état du serveur</a></p>'
                    ).encode("utf-8")
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
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    def qr_png(self) -> bytes:
        """Génère un QR code contenant l'URL du serveur."""
        try:
            import qrcode
        except ImportError as exc:
            raise RuntimeError("Installez la dépendance 'qrcode' (pip install qrcode[pil]).") from exc

        image = qrcode.make(self.base_url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
