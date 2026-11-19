"""Page de configuration visuelle de la synchronisation (sans transport réseau raccordé)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class TkSyncView:
    """Présente les réglages client/serveur; les actions réseau restent désactivées fonctionnellement."""

    def __init__(self, parent):
        self._status = tk.StringVar(value="Synchronisation non configurée")
        ttk.Label(parent, text="Se connecter à un serveur", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(4, 8))
        ttk.Label(parent, text="Adresse du serveur").pack(anchor="w")
        self._url = tk.StringVar(value="http://127.0.0.1:8765")
        ttk.Entry(parent, textvariable=self._url, width=55).pack(anchor="w", pady=(4, 6))
        ttk.Label(parent, text="Adresse locale ou URL fournie par la personne qui partage les données.",
                  foreground="#555").pack(anchor="w", pady=(0, 16))

        ttk.Separator(parent).pack(fill="x", pady=8)
        ttk.Label(parent, text="Héberger sur cet ordinateur", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(4, 8))
        ttk.Label(parent, text="Port local").pack(anchor="w")
        self._port = tk.StringVar(value="8765")
        ttk.Entry(parent, textvariable=self._port, width=12).pack(anchor="w", pady=(4, 6))
        ttk.Label(parent, text="Le serveur n'est pas démarré. L'accès réseau et le partage ne sont pas encore activés.",
                  foreground="#555", wraplength=850, justify="left").pack(anchor="w", pady=(0, 12))

        actions = ttk.Frame(parent)
        actions.pack(anchor="w", pady=(4, 10))
        for text in ("Tester la connexion", "Synchroniser maintenant", "Démarrer le serveur"):
            ttk.Button(actions, text=text, command=self._not_available).pack(side="left", padx=(0, 8))
        ttk.Label(parent, textvariable=self._status, foreground="#2B7DE9", wraplength=850,
                  justify="left").pack(anchor="w", pady=(8, 6))
        ttk.Label(parent, text="Cette page est une maquette de configuration. Elle n'envoie aucune donnée et n'ouvre aucun port.",
                  foreground="#555", wraplength=850, justify="left").pack(anchor="w")

    def _not_available(self) -> None:
        self._status.set("Non disponible : le service de synchronisation n'est pas encore implémenté.")
