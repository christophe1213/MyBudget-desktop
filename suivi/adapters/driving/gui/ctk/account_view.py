"""Carte « utilisateur connecté » au bas de la barre latérale, avec le bouton de déconnexion."""
from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from ..contract.interfaces import AccountListener, AccountView
from . import theme as t
from .widgets import call

CARD = "#1C6339"   # vert un peu plus foncé que la barre latérale


class CtkAccountView(AccountView):
    def __init__(self, parent):
        self._listener: Optional[AccountListener] = None
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12)
        card.pack(side="bottom", fill="x", padx=16, pady=(0, 8))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 8))
        self._avatar = ctk.CTkLabel(top, text="?", width=38, height=38, corner_radius=19, fg_color=t.WHITE,
                                    text_color=t.GREEN, font=t.font(15, "bold"))
        self._avatar.pack(side="left")
        names = ctk.CTkFrame(top, fg_color="transparent")
        names.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self._name = ctk.CTkLabel(names, text="", font=t.font(13, "bold"), text_color=t.WHITE, anchor="w")
        self._name.pack(anchor="w")
        self._email = ctk.CTkLabel(names, text="", font=t.font(11), text_color=t.SIDEBAR_MUTED, anchor="w")
        self._email.pack(anchor="w")
        ctk.CTkButton(card, text="Se déconnecter", command=lambda: call(lambda: self._listener, "on_logout"),
                      height=32, corner_radius=8, fg_color="transparent", hover_color=t.SIDEBAR_HOVER,
                      text_color=t.WHITE, border_width=1, border_color=t.SIDEBAR_MUTED,
                      font=t.font(12, "bold")).pack(fill="x", padx=12, pady=(0, 12))

    def set_listener(self, listener: AccountListener) -> None:
        self._listener = listener

    def show_user(self, name: str, email: str) -> None:
        self._avatar.configure(text=(name.strip()[:1] or "?").upper())
        self._name.configure(text=name)
        self._email.configure(text=email)
