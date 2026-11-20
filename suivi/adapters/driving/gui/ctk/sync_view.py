"""Page de synchronisation utilisant le serveur HTTP local."""
from __future__ import annotations

import io

import customtkinter as ctk

from . import theme as t
from ...sync_server import SyncHTTPServer
from .widgets import button, label


class CtkSyncView:
    def __init__(self, parent):
        self._server: SyncHTTPServer | None = None
        self._status = ctk.StringVar(value="Synchronisation arrêtée")
        self._server_port = ctk.StringVar(value="8765")
        self._qr = None

        panel = ctk.CTkFrame(parent, fg_color=t.SURFACE, corner_radius=10)
        panel.pack(fill="x", pady=(0, 14))
        label(panel, "Serveur de synchronisation", "strong").pack(anchor="w", padx=18, pady=(16, 8))
        ctk.CTkLabel(panel, text="Port local", text_color=t.TEXT).pack(anchor="w", padx=18)
        self._port_entry = ctk.CTkEntry(panel, textvariable=self._server_port, width=120)
        self._port_entry.pack(anchor="w", padx=18, pady=(4, 10))
        label(panel, "Le serveur écoute sur toutes les interfaces réseau de cet ordinateur.",
              "muted", wraplength=800).pack(anchor="w", padx=18, pady=(0, 14))

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 12))
        self._start_button = button(actions, "Démarrer le serveur", self.start, "primary", 180)
        self._start_button.pack(side="left")
        self._stop_button = button(actions, "Arrêter", self.stop, "danger", 100)
        self._stop_button.pack(side="left", padx=10)

        ctk.CTkLabel(parent, textvariable=self._status, text_color=t.BLUE,
                     anchor="w", wraplength=900).pack(fill="x", pady=(4, 8))
        self._qr_label = ctk.CTkLabel(parent, text="", width=260, height=260)
        self._qr_label.pack(anchor="w", pady=(4, 8))
        label(parent, "Connectez un appareil au même réseau Wi-Fi, puis flashez le QR code."
              " L'échange de données financières sera ajouté ensuite.",
              "muted", wraplength=900).pack(anchor="w")

    def start(self) -> None:
        if self._server is not None and self._server.running:
            self._status.set("Serveur déjà actif.")
            return
        try:
            port = int(self._server_port.get().strip())
            self._server = SyncHTTPServer(port)
            url = self._server.start()
            self._status.set(f"Serveur actif : {url}")
            self._show_qr()
        except (ValueError, OSError, RuntimeError) as exc:
            self._server = None
            self._status.set(f"Impossible de démarrer le serveur : {exc}")

    def stop(self) -> None:
        if self._server is not None:
            self._server.stop()
        self._server = None
        self._qr_label.configure(image="", text="")
        self._qr = None
        self._status.set("Serveur arrêté.")

    def _show_qr(self) -> None:
        try:
            from PIL import Image
            png = self._server.qr_png()
            image = Image.open(io.BytesIO(png)).resize((260, 260))
            self._qr = ctk.CTkImage(light_image=image, dark_image=image, size=(260, 260))
            self._qr_label.configure(image=self._qr, text="")
        except (ImportError, RuntimeError, OSError) as exc:
            self._status.set(f"Serveur actif, mais QR code indisponible : {exc}")
