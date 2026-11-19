"""Barre du haut : portefeuille actif, solde initial, import, ouverture du fichier de données."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.interfaces import HeaderListener, HeaderView
from .widgets import button, call, combo, entry, label


class CtkHeaderView(HeaderView):
    def __init__(self, root, parent):
        self._root = root
        self._listener: Optional[HeaderListener] = None
        self._wallet = ctk.StringVar()
        self._balance = ctk.StringVar()

        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=28, pady=14)
        label(bar, "Portefeuille", "muted").pack(side="left", padx=(0, 8))
        self._combo = combo(bar, self._wallet, 190,
                            command=lambda choice: call(self._get, "on_wallet_selected", choice))
        self._combo.pack(side="left")
        label(bar, "Solde initial (Ar)", "muted").pack(side="left", padx=(28, 8))
        entry(bar, self._balance, 120).pack(side="left")
        button(bar, "Appliquer", lambda: call(self._get, "on_apply_initial_balance"), "secondary", 96).pack(
            side="left", padx=8)
        button(bar, "Ouvrir le fichier", lambda: call(self._get, "on_open_storage"), "secondary").pack(side="right")
        button(bar, "Importer…", lambda: call(self._get, "on_import"), "secondary").pack(side="right", padx=8)

    def _get(self):
        return self._listener

    def set_listener(self, listener: HeaderListener) -> None:
        self._listener = listener

    def show_wallets(self, names: Sequence[str], active: str) -> None:
        self._combo.configure(values=list(names))
        self._wallet.set(active)

    def show_initial_balance(self, text: str) -> None:
        self._balance.set(text)

    def get_initial_balance_text(self) -> str:
        return self._balance.get()

    def set_window_title(self, text: str) -> None:
        self._root.title(text)
