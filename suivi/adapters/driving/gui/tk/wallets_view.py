"""Onglet « Portefeuilles »."""
from __future__ import annotations

from tkinter import ttk
from typing import Optional, Sequence

from ..contract.dto import Row
from ..contract.interfaces import WalletsListener, WalletsView
from .widgets import Column, Table, call


class TkWalletsView(WalletsView):
    def __init__(self, parent):
        self._listener: Optional[WalletsListener] = None
        ttk.Label(parent, foreground="#555",
                  text="Un portefeuille = un fichier Excel de transactions (banque, caisse, ...).").pack(
            anchor="w", pady=(0, 6))
        self._table = Table(parent, [Column("name", "Portefeuille", 200), Column("file", "Fichier", 300),
                                     Column("count", "Transactions", 110, "e"),
                                     Column("balance", "Solde actuel", 150, "e")])
        self._table.on_double_click(self._double_click)
        self._total = ttk.Label(parent, text="", font=("Arial", 10, "bold"))
        self._total.pack(anchor="w", pady=(6, 0))

        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=(6, 0))
        for text, method, pad in [("Ouvrir", "on_open", (0, 6)), ("Nouveau…", "on_new", (0, 6)),
                                  ("Ajouter un fichier existant…", "on_link_file", (0, 6)),
                                  ("Renommer…", "on_rename", (0, 6)), ("Retirer de la liste", "on_remove", 0)]:
            ttk.Button(buttons, text=text, command=lambda m=method: call(self._get, m)).pack(
                side="left", padx=pad)
        ttk.Label(parent, foreground="#555", wraplength=900, justify="left",
                  text="« ● » = portefeuille ouvert. Double-clic pour ouvrir un portefeuille. "
                       "Chaque portefeuille a ses propres catégories, budgets et solde initial. "
                       "« Retirer » ne supprime jamais le fichier Excel.").pack(anchor="w", pady=(6, 0))

    def _get(self):
        return self._listener

    def _double_click(self) -> None:
        if self._table.selected_id() is not None:
            call(self._get, "on_open", False)

    def set_listener(self, listener: WalletsListener) -> None:
        self._listener = listener

    def show_wallets(self, rows: Sequence[Row], total_text: str) -> None:
        self._table.show(rows)
        self._total.config(text=total_text)

    def get_selected_id(self) -> Optional[str]:
        return self._table.selected_id()
