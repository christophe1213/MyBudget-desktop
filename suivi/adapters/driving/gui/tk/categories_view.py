"""Onglet « Catégories » : ajouter, renommer, supprimer."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence

from ..contract.dto import Row
from ..contract.interfaces import CategoryManagerListener, CategoryManagerView
from .widgets import Column, Table, call


class TkCategoryManagerView(CategoryManagerView):
    def __init__(self, parent):
        self._listener: Optional[CategoryManagerListener] = None
        self._new_name = tk.StringVar()

        add = ttk.LabelFrame(parent, text="Ajouter une catégorie", padding=10)
        add.pack(fill="x")
        entry = ttk.Entry(add, textvariable=self._new_name, width=30)
        entry.pack(side="left", padx=(0, 8))
        entry.bind("<Return>", lambda _e: call(self._get, "on_add"))
        ttk.Button(add, text="Ajouter", command=lambda: call(self._get, "on_add")).pack(side="left")

        ttk.Label(parent, text="Catégories existantes", font=("Arial", 11, "bold")).pack(anchor="w",
                                                                                      pady=(12, 4))
        self._table = Table(parent, [Column("name", "Catégorie", 260),
                                     Column("count", "Nb de transactions", 160, "e"),
                                     Column("budget", "Budget / jour", 140, "e")])
        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Renommer", command=lambda: call(self._get, "on_rename")).pack(side="left")
        ttk.Button(buttons, text="Supprimer", command=lambda: call(self._get, "on_delete")).pack(
            side="left", padx=6)
        ttk.Label(parent, foreground="#555",
                  text="Renommer met aussi à jour les transactions existantes. "
                       "Une catégorie utilisée par des transactions ne peut pas être supprimée.").pack(
            anchor="w", pady=(6, 0))

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
