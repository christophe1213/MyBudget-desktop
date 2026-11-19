"""Onglets « Solde par date » et « Détail par catégorie »."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence

from ..contract.dto import Row
from ..contract.interfaces import BalanceView, CategoryDetailListener, CategoryDetailView
from .widgets import Column, Table, call


class TkBalanceView(BalanceView):
    def __init__(self, parent):
        self._table = Table(parent, [Column("date", "Date", 120), Column("deposits", "Dépôts", 140, "e"),
                                     Column("expenses", "Dépenses", 140, "e"),
                                     Column("balance", "Solde fin de journée", 180, "e")])

    def show_rows(self, rows: Sequence[Row]) -> None:
        self._table.show(rows)


class TkCategoryDetailView(CategoryDetailView):
    def __init__(self, parent):
        self._listener: Optional[CategoryDetailListener] = None
        self._category = tk.StringVar()
        self._date = tk.StringVar()

        filters = ttk.Frame(parent)
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="Catégorie :").pack(side="left")
        self._category_combo = ttk.Combobox(filters, textvariable=self._category, width=16, state="readonly")
        self._category_combo.pack(side="left", padx=(4, 14))
        ttk.Label(filters, text="Date :").pack(side="left")
        self._date_combo = ttk.Combobox(filters, textvariable=self._date, width=12, state="readonly")
        self._date_combo.pack(side="left", padx=4)
        for combo in (self._category_combo, self._date_combo):
            combo.bind("<<ComboboxSelected>>", lambda _e: call(self._get, "on_filter_changed"))

        self._table = Table(parent, [Column("date", "Date", 110), Column("category", "Catégorie", 140),
                                     Column("deposits", "Dépôts", 120, "e"),
                                     Column("expenses", "Dépenses", 120, "e"),
                                     Column("net", "Net", 120, "e"),
                                     Column("balance", "Solde cumulé catégorie", 170, "e")])
        self._totals = ttk.Label(parent, text="", font=("Arial", 10, "bold"))
        self._totals.pack(anchor="w", pady=(6, 0))

    def _get(self):
        return self._listener

    def set_listener(self, listener: CategoryDetailListener) -> None:
        self._listener = listener

    def set_filter_options(self, categories: Sequence[str], dates: Sequence[str]) -> None:
        self._category_combo["values"] = list(categories)
        self._date_combo["values"] = list(dates)

    def get_filters(self) -> tuple[str, str]:
        return self._category.get(), self._date.get()

    def set_filters(self, category: str, date: str) -> None:
        self._category.set(category)
        self._date.set(date)

    def show_rows(self, rows: Sequence[Row]) -> None:
        self._table.show(rows)

    def show_totals(self, text: str) -> None:
        self._totals.config(text=text)
