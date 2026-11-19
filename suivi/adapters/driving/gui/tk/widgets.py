"""Petits composants Tkinter réutilisés par plusieurs vues (aucune logique métier)."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Optional, Sequence

from ..contract.dto import Row
from ..view_support import call  # noqa: F401  (réexporté pour les vues)


@dataclass(frozen=True)
class Column:
    id: str
    title: str
    width: int
    anchor: str = "w"


class Table:
    """Tableau (Treeview) avec barre de défilement. Les lignes arrivent déjà mises en forme."""

    def __init__(self, parent, columns: Sequence[Column], height: Optional[int] = None):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        options = {"height": height} if height else {}
        self.tree = ttk.Treeview(frame, columns=[c.id for c in columns], show="headings", **options)
        for c in columns:
            self.tree.heading(c.id, text=c.title)
            self.tree.column(c.id, width=c.width, anchor=c.anchor)
        self.tree.tag_configure("emphasis", font=("Arial", 10, "bold"))
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def show(self, rows: Sequence[Row], selected_id: Optional[str] = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", iid=row.id, values=row.values,
                             tags=("emphasis",) if row.emphasis else ())
        if selected_id is not None and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)

    def selected_ids(self) -> list[str]:
        return list(self.tree.selection())

    def selected_id(self) -> Optional[str]:
        ids = self.selected_ids()
        return ids[0] if ids else None

    def on_double_click(self, callback: Callable[[], None]) -> None:
        self.tree.bind("<Double-1>", lambda _event: callback())
