"""Page « Catégories » : ajouter, renommer, supprimer."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from ..contract.interfaces import CategoryManagerListener, CategoryManagerView
from .widgets import Column, Table, button, call, card, entry, label


class CtkCategoryManagerView(CategoryManagerView):
    def __init__(self, parent):
        self._listener: Optional[CategoryManagerListener] = None
        self._new_name = ctk.StringVar()

        add = card(parent)
        add.pack(fill="x", pady=(0, 14))
        label(add, "Ajouter une catégorie", "section").pack(anchor="w", padx=20, pady=(16, 8))
        row = ctk.CTkFrame(add, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        name = entry(row, self._new_name, 320)
        name.pack(side="left", padx=(0, 12))
        name.bind("<Return>", lambda _e: call(self._get, "on_add"))
        button(row, "Ajouter", lambda: call(self._get, "on_add"), "primary", 110).pack(side="left")

        self._table = Table(parent, [Column("name", "Catégorie", 280), Column("count", "Transactions", 150, "e"),
                                     Column("budget", "Budget / jour", 160, "e")])
        buttons = ctk.CTkFrame(parent, fg_color="transparent")
        buttons.pack(fill="x", pady=(12, 0))
        button(buttons, "Renommer", lambda: call(self._get, "on_rename"), "secondary", 120).pack(side="left")
        button(buttons, "Supprimer", lambda: call(self._get, "on_delete"), "danger", 120).pack(side="left", padx=10)
        label(parent, "Renommer met aussi à jour les transactions existantes. "
                      "Une catégorie utilisée par des transactions ne peut pas être supprimée.",
              "muted", wraplength=900).pack(anchor="w", pady=(10, 0))

    def _get(self):
        return self._listener

    def set_listener(self, listener: CategoryManagerListener) -> None:
        self._listener = listener

    def get_new_name(self) -> str:
        return self._new_name.get()

    def clear_new_name(self) -> None:
        self._new_name.set("")

    def show_categories(self, rows: Sequence[Row]) -> None:
        self._table.show(rows)

    def get_selected_id(self) -> Optional[str]:
        return self._table.selected_id()
