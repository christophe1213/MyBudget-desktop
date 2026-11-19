"""Page de configuration visuelle de la synchronisation (sans transport réseau raccordé)."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as t
from .widgets import button, label


class CtkSyncView:
    """Présente les réglages client/serveur; les actions réseau restent désactivées fonctionnellement."""

    def __init__(self, parent):
        self._status = ctk.StringVar(value="Synchronisation non configurée")
        self._server_url = ctk.StringVar(value="http://127.0.0.1:8765")
        self._server_port = ctk.StringVar(value="8765")

        panel = ctk.CTkFrame(parent, fg_color=t.SURFACE, corner_radius=10)
        panel.pack(fill="x", pady=(0, 14))
        label(panel, "Se connecter à un serveur", "strong").pack(anchor="w", padx=18, pady=(16, 8))
        ctk.CTkLabel(panel, text="Adresse du serveur", text_color=t.TEXT).pack(anchor="w", padx=18)
        self._url_entry = ctk.CTkEntry(panel, textvariable=self._server_url, width=420)
        self._url_entry.pack(anchor="w", padx=18, pady=(4, 10))
        label(panel, "Adresse locale ou URL fournie par la personne qui partage les données.",
              "muted", wraplength=800).pack(anchor="w", padx=18, pady=(0, 14))

        server_panel = ctk.CTkFrame(parent, fg_color=t.SURFACE, corner_radius=10)
        server_panel.pack(fill="x", pady=(0, 14))
        label(server_panel, "Héberger sur cet ordinateur", "strong").pack(anchor="w", padx=18, pady=(16, 8))
        ctk.CTkLabel(server_panel, text="Port local", text_color=t.TEXT).pack(anchor="w", padx=18)
        self._port_entry = ctk.CTkEntry(server_panel, textvariable=self._server_port, width=120)
        self._port_entry.pack(anchor="w", padx=18, pady=(4, 10))
        label(server_panel, "Le serveur n'est pas démarré. L'accès réseau et le partage ne sont pas encore activés.",
              "muted", wraplength=800).pack(anchor="w", padx=18, pady=(0, 14))

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 12))
        button(actions, "Tester la connexion", self._not_available, "secondary", 180).pack(side="left")
        button(actions, "Synchroniser maintenant", self._not_available, "primary", 210).pack(side="left", padx=10)
        button(actions, "Démarrer le serveur", self._not_available, "secondary", 180).pack(side="left")

        ctk.CTkLabel(parent, textvariable=self._status, text_color=t.BLUE,
                     anchor="w", wraplength=900).pack(fill="x", pady=(4, 8))
        label(parent, "Cette page est une maquette de configuration. Elle n'envoie aucune donnée et n'ouvre aucun port.",
              "muted", wraplength=900).pack(anchor="w")

    def _not_available(self) -> None:
        self._status.set("Non disponible : le service de synchronisation n'est pas encore implémenté.")
