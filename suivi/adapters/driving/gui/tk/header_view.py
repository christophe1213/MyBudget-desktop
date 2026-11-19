"""Barre du haut : portefeuille actif, solde initial, import, ouverture du fichier Excel."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence

from ..contract.interfaces import HeaderListener, HeaderView
from .widgets import call


class TkHeaderView(HeaderView):
    def __init__(self, root, parent):
        self._root = root
        self._listener: Optional[HeaderListener] = None
        self._wallet = tk.StringVar()
        self._balance = tk.StringVar()

        ttk.Label(parent, text="Portefeuille :", font=("Arial", 10, "bold")).pack(side="left")
        self._combo = ttk.Combobox(parent, textvariable=self._wallet, width=18, state="readonly")
        self._combo.pack(side="left", padx=(4, 16))
        self._combo.bind("<<ComboboxSelected>>",
                         lambda _e: call(self._get, "on_wallet_selected", self._wallet.get()))
        ttk.Label(parent, text="Solde initial (Ar) :").pack(side="left")
        ttk.Entry(parent, textvariable=self._balance, width=12).pack(side="left", padx=4)
        ttk.Button(parent, text="Appliquer",
                   command=lambda: call(self._get, "on_apply_initial_balance")).pack(side="left")
        ttk.Button(parent, text="Ouvrir le fichier",
                   command=lambda: call(self._get, "on_open_storage")).pack(side="right")
        ttk.Button(parent, text="Importer un Excel…",
                   command=lambda: call(self._get, "on_import")).pack(side="right", padx=6)

    def _get(self):
        return self._listener

    def set_listener(self, listener: HeaderListener) -> None:
        self._listener = listener

    def show_wallets(self, names: Sequence[str], active: str) -> None:
        self._combo["values"] = list(names)
        self._wallet.set(active)

    def show_initial_balance(self, text: str) -> None:
        self._balance.set(text)

    def get_initial_balance_text(self) -> str:
        return self._balance.get()

    def set_window_title(self, text: str) -> None:
        self._root.title(text)
