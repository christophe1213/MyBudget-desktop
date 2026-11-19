"""Page de synchronisation utilisant le serveur HTTP local."""
from __future__ import annotations

import io
import tkinter as tk
from tkinter import ttk

from . import theme as t
from ...driven.sync_server import SyncHTTPServer


class TkSyncView:
    def __init__(self, parent):
        del t
        self._server: SyncHTTPServer | None = None
        self._status = tk.StringVar(value="Synchronisation arrêtée")
        self._server_port = tk.StringVar(value="8765")
        self._qr_image = None

        ttk.Label(parent, text="Serveur de synchronisation", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(4, 8))
        ttk.Label(parent, text="Port local").pack(anchor="w")
        ttk.Entry(parent, textvariable=self._server_port, width=12).pack(anchor="w", pady=(4, 6))
        ttk.Label(parent, text="Le serveur écoute sur toutes les interfaces réseau de cet ordinateur.",
                  foreground="#555").pack(anchor="w", pady=(0, 12))

        actions = ttk.Frame(parent)
        actions.pack(anchor="w", pady=(4, 10))
        ttk.Button(actions, text="Démarrer le serveur", command=self.start).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Arrêter", command=self.stop).pack(side="left")

        ttk.Label(parent, textvariable=self._status, foreground="#2B7DE9", wraplength=850,
                  justify="left").pack(anchor="w", pady=(8, 6))
        self._qr_label = ttk.Label(parent)
        self._qr_label.pack(anchor="w", pady=(4, 8))
        ttk.Label(parent, text="Connectez un appareil au même réseau Wi-Fi, puis flashez le QR code. "
                              "L'échange de données financières sera ajouté ensuite.",
                  foreground="#555", wraplength=850, justify="left").pack(anchor="w")

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
        self._qr_label.configure(image="")
        self._qr_image = None
        self._status.set("Serveur arrêté.")

    def _show_qr(self) -> None:
        try:
            from PIL import Image, ImageTk
            png = self._server.qr_png()
            image = Image.open(io.BytesIO(png)).resize((260, 260))
            self._qr_image = ImageTk.PhotoImage(image)
            self._qr_label.configure(image=self._qr_image)
        except (ImportError, RuntimeError, OSError) as exc:
            self._status.set(f"Serveur actif, mais QR code indisponible : {exc}")
