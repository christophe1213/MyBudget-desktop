"""Page « Portefeuilles »."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from ..contract.interfaces import WalletsListener, WalletsView
from . import theme as t
from .widgets import Column, Table, button, call, label, tinted


class CtkWalletsView(WalletsView):
    def __init__(self, parent):
        self._listener: Optional[WalletsListener] = None
        self._table = Table(parent, [Column("name", "Portefeuille", 220), Column("file", "Emplacement", 320),
                                     Column("count", "Transactions", 120, "e"), Column("balance", "Solde actuel", 170, "e")])
        self._table.on_double_click(self._double_click)
        box = tinted(parent)
        box.pack(fill="x", pady=12)
        self._total = label(box, "", "strong", color=t.GREEN)
        self._total.pack(anchor="w", padx=16, pady=10)

        buttons = ctk.CTkFrame(parent, fg_color="transparent")
        buttons.pack(fill="x")
        button(buttons, "Ouvrir", lambda: call(self._get, "on_open"), "primary", 100).pack(side="left")
        for text, method, width in [("Nouveau…", "on_new", 120), ("Ajouter un fichier existant…", "on_link_file", 230),
                                    ("Renommer…", "on_rename", 130)]:
            button(buttons, text, lambda m=method: call(self._get, m), "secondary", width).pack(side="left", padx=(10, 0))
        button(buttons, "Retirer de la liste", lambda: call(self._get, "on_remove"), "danger", 170).pack(
            side="left", padx=(10, 0))
        label(parent, "« ● » = portefeuille ouvert. Double-clic pour ouvrir un portefeuille. Chaque portefeuille a "
                      "ses propres catégories, budgets et solde initial. « Retirer » ne supprime jamais le stockage.",
              "muted", wraplength=1000).pack(anchor="w", pady=(10, 0))

    def _get(self):
        return self._listener

    def _double_click(self) -> None:
        if self._table.selected_id() is not None:
            call(self._get, "on_open", False)

    def set_listener(self, listener: WalletsListener) -> None:
        self._listener = listener

    def show_wallets(self, rows: Sequence[Row], total_text: str) -> None:
        self._table.show(rows)
        self._total.configure(text=total_text)

    def get_selected_id(self) -> Optional[str]:
        return self._table.selected_id()
