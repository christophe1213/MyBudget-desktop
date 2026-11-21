"""Onglet de synchronisation : serveur WebSocket local, envoi / récupération des données, journal."""
from __future__ import annotations

import io
from typing import Optional, Sequence

import customtkinter as ctk

from . import theme as t
from ..contract.interfaces import SyncListener, SyncView
from ...sync_server import SyncEvent, SyncHTTPServer
from .widgets import button, entry, label

POLL_MS = 150   # fréquence à laquelle les événements du réseau sont repris dans le thread de l'interface


class CtkSyncView(SyncView):
    def __init__(self, parent):
        self._parent = parent
        self._listener: Optional[SyncListener] = None
        self._server: SyncHTTPServer | None = None
        self._after_id = None
        self._status = ctk.StringVar(value="Synchronisation arrêtée")
        self._server_port = ctk.StringVar(value="8765")
        self._start_date = ctk.StringVar(value="")
        self._devices = ctk.StringVar(value="Appareils connectés : 0")
        self._journal_location = ctk.StringVar(value="")
        self._qr = None

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))
        self._qr_label = ctk.CTkLabel(top, text="", width=200, height=200)
        self._qr_label.pack(side="right", padx=(12, 0))
        panel = ctk.CTkFrame(top, fg_color=t.SURFACE, corner_radius=10)
        panel.pack(side="left", fill="both", expand=True)
        label(panel, "Serveur de synchronisation", "strong").pack(anchor="w", padx=18, pady=(14, 6))
        ctk.CTkLabel(panel, text="Port local", text_color=t.TEXT).pack(anchor="w", padx=18)
        self._port_entry = ctk.CTkEntry(panel, textvariable=self._server_port, width=120)
        self._port_entry.pack(anchor="w", padx=18, pady=(4, 8))
        label(panel, "Flashez le QR code avec l'appareil (même Wi-Fi) : il contient le jeton d'appairage. "
                     "Le trafic n'est pas chiffré : réseau de confiance seulement.",
              "muted", wraplength=520).pack(anchor="w", padx=18, pady=(0, 8))
        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(anchor="w", padx=18, pady=(0, 14))
        self._start_button = button(actions, "Démarrer le serveur", self.start, "primary", 180)
        self._start_button.pack(side="left")
        self._stop_button = button(actions, "Arrêter", self.stop, "danger", 100)
        self._stop_button.pack(side="left", padx=10)

        ctk.CTkLabel(parent, textvariable=self._status, text_color=t.BLUE,
                     anchor="w", wraplength=900).pack(fill="x", pady=(0, 6))

        exchange = ctk.CTkFrame(parent, fg_color=t.SURFACE, corner_radius=10)
        exchange.pack(fill="x", pady=(0, 8))
        label(exchange, "Échange de données", "strong").pack(anchor="w", padx=18, pady=(14, 6))
        row = ctk.CTkFrame(exchange, fg_color="transparent")
        row.pack(anchor="w", padx=18)
        label(row, "Envoyer à partir du (JJ/MM/AAAA)").pack(side="left", padx=(0, 10))
        entry(row, self._start_date, 130).pack(side="left")
        label(exchange, "Vide = tout l'historique. Les opérations antérieures à cette date sont résumées dans les "
                        "soldes de départ des catégories.", "muted", wraplength=800).pack(anchor="w", padx=18, pady=(4, 8))
        buttons = ctk.CTkFrame(exchange, fg_color="transparent")
        buttons.pack(anchor="w", padx=18, pady=(0, 6))
        button(buttons, "Envoyer", lambda: self._act("on_send"), "primary", 140).pack(side="left")
        button(buttons, "Récupérer", lambda: self._act("on_fetch"), "secondary", 140).pack(side="left", padx=10)
        ctk.CTkLabel(exchange, textvariable=self._devices, text_color=t.TEXT, anchor="w").pack(
            anchor="w", padx=18, pady=(0, 12))

        label(parent, "Journal de synchronisation", "strong").pack(anchor="w")
        ctk.CTkLabel(parent, textvariable=self._journal_location, text_color=t.MUTED, anchor="w").pack(fill="x")
        self._log = ctk.CTkTextbox(parent, height=170, fg_color=t.SURFACE, text_color=t.TEXT, font=t.font(12))
        self._log.pack(fill="both", expand=True, pady=(4, 0))
        self._log.configure(state="disabled")

    # ---- contrat SyncView -------------------------------------------------------------------------------
    def set_listener(self, listener: SyncListener) -> None:
        self._listener = listener

    def start_date_text(self) -> str:
        return self._start_date.get()

    def device_count(self) -> int:
        return self._server.client_count if self._server is not None and self._server.running else 0

    def send(self, text: str, client: Optional[int] = None) -> int:
        if self._server is None or not self._server.running:
            return 0
        return self._server.send(text, client)

    def show_message(self, line: str) -> None:
        self._write([line], replace=False)

    def show_journal(self, lines: Sequence[str], location: str) -> None:
        self._journal_location.set(f"Fichier : {location}")
        self._write(lines, replace=True)

    # ---- serveur ------------------------------------------------------------------------------------------
    def start(self) -> None:
        if self._server is not None and self._server.running:
            self._status.set("Serveur déjà actif.")
            return
        try:
            port = int(self._server_port.get().strip())
            self._server = SyncHTTPServer(port)
            self._server.start()
            self._status.set(f"Serveur actif : {self._server.pairing_url}")   # même adresse que le QR code
            self._show_qr()
            self._schedule()
        except (ValueError, OSError, RuntimeError) as exc:
            self._server = None
            self._status.set(f"Impossible de démarrer le serveur : {exc}")

    def stop(self) -> None:
        if self._after_id is not None:
            self._parent.after_cancel(self._after_id)
            self._after_id = None
        if self._server is not None:
            self._server.stop()
        self._server = None
        self._qr_label.configure(image="", text="")
        self._qr = None
        self._devices.set("Appareils connectés : 0")
        self._status.set("Serveur arrêté.")

    def _schedule(self) -> None:
        self._after_id = self._parent.after(POLL_MS, self._pump)

    def _pump(self) -> None:
        """Reprend, dans le thread de l'interface, les événements déposés par les threads du serveur."""
        self._after_id = None
        server = self._server
        if server is None or not server.running:
            return
        for event in server.poll():
            self._dispatch(event)
        self._devices.set(f"Appareils connectés : {server.client_count}")
        self._schedule()

    def _dispatch(self, event: SyncEvent) -> None:
        if self._listener is None:
            return
        try:
            if event.kind == "connected":
                self._listener.on_device_connected(event.client, event.address)
            elif event.kind == "disconnected":
                self._listener.on_device_disconnected(event.client, event.address)
            else:
                self._listener.on_message(event.client, event.address, event.text)
        except Exception as exc:  # noqa: BLE001  (un message défectueux ne doit pas arrêter la synchronisation)
            self.show_message(f"Erreur inattendue : {exc}")

    def _act(self, name: str) -> None:
        if self._listener is not None:
            getattr(self._listener, name)()

    def _write(self, lines: Sequence[str], replace: bool) -> None:
        self._log.configure(state="normal")
        if replace:
            self._log.delete("1.0", "end")
        for line in lines:
            self._log.insert("end", line + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _show_qr(self) -> None:
        try:
            from PIL import Image
            png = self._server.qr_png()
            image = Image.open(io.BytesIO(png)).resize((200, 200))
            self._qr = ctk.CTkImage(light_image=image, dark_image=image, size=(200, 200))
            self._qr_label.configure(image=self._qr, text="")
        except (ImportError, RuntimeError, OSError) as exc:
            self._status.set(f"Serveur actif, mais QR code indisponible : {exc}")
