"""Pages « Solde par date » et « Détail par catégorie »."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from ..contract.interfaces import BalanceView, CategoryDetailListener, CategoryDetailView
from . import theme as t
from .widgets import Column, Table, call, card, combo, field, label, tinted


class CtkBalanceView(BalanceView):
    def __init__(self, parent):
        self._table = Table(parent, [Column("date", "Date", 140), Column("deposits", "Dépôts", 160, "e"),
                                     Column("expenses", "Dépenses", 160, "e"),
                                     Column("balance", "Solde fin de journée", 200, "e")])

    def show_rows(self, rows: Sequence[Row]) -> None:
        self._table.show(rows)


class CtkCategoryDetailView(CategoryDetailView):
    def __init__(self, parent):
        self._listener: Optional[CategoryDetailListener] = None
        self._category = ctk.StringVar()
        self._date = ctk.StringVar()

        filters = card(parent)
        filters.pack(fill="x", pady=(0, 14))
        row = ctk.CTkFrame(filters, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)
        column = field(row, "Catégorie")
        column.pack(side="left", padx=(0, 16))
        self._category_combo = combo(column, self._category, 200, lambda _c: call(self._get, "on_filter_changed"))
        self._category_combo.pack(anchor="w")
        column = field(row, "Date")
        column.pack(side="left")
        self._date_combo = combo(column, self._date, 160, lambda _c: call(self._get, "on_filter_changed"))
        self._date_combo.pack(anchor="w")

        self._table = Table(parent, [Column("date", "Date", 120), Column("category", "Catégorie", 160),
                                     Column("deposits", "Dépôts", 130, "e"), Column("expenses", "Dépenses", 130, "e"),
                                     Column("net", "Net", 130, "e"),
                                     Column("balance", "Solde cumulé catégorie", 190, "e")])
        box = tinted(parent)
        box.pack(fill="x", pady=(12, 0))
        self._totals = label(box, "", "strong", color=t.GREEN)
        self._totals.pack(anchor="w", padx=16, pady=10)

    def _get(self):
        return self._listener

    def set_listener(self, listener: CategoryDetailListener) -> None:
        self._listener = listener

    def set_filter_options(self, categories: Sequence[str], dates: Sequence[str]) -> None:
        self._category_combo.configure(values=list(categories))
        self._date_combo.configure(values=list(dates))

    def get_filters(self) -> tuple[str, str]:
        return self._category.get(), self._date.get()

    def set_filters(self, category: str, date: str) -> None:
        self._category.set(category)
        self._date.set(date)

    def show_rows(self, rows: Sequence[Row]) -> None:
        self._table.show(rows)

    def show_totals(self, text: str) -> None:
        self._totals.configure(text=text)
