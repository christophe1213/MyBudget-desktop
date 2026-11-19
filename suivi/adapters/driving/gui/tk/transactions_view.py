"""Onglet « Saisie »."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Optional, Sequence

from .....domain.model.transaction import Kind
from ..contract.dto import Row, TransactionForm
from ..contract.interfaces import TransactionsListener, TransactionsView
from .widgets import Column, Table, call


KINDS = tuple(k.value for k in Kind)


class TkTransactionsView(TransactionsView):
    def __init__(self, parent):
        self._listener: Optional[TransactionsListener] = None
        self._date = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self._category = tk.StringVar()
        self._kind = tk.StringVar(value=KINDS[0])
        self._label = tk.StringVar()
        self._amount = tk.StringVar()

        form = ttk.LabelFrame(parent, text="Nouvelle transaction", padding=10)
        form.pack(fill="x")
        for col, title in enumerate(["Date", "Catégorie", "Type", "Libellé", "Montant (Ar)"]):
            ttk.Label(form, text=title).grid(row=0, column=col, sticky="w")
        ttk.Entry(form, textvariable=self._date, width=12).grid(row=1, column=0, padx=(0, 8))
        self._combo = ttk.Combobox(form, textvariable=self._category, width=16, state="readonly")
        self._combo.grid(row=1, column=1, padx=(0, 8))
        ttk.Combobox(form, textvariable=self._kind, values=list(KINDS), width=10,
                     state="readonly").grid(row=1, column=2, padx=(0, 8))
        self._label_entry = ttk.Entry(form, textvariable=self._label, width=28)
        self._label_entry.grid(row=1, column=3, padx=(0, 8))
        amount_entry = ttk.Entry(form, textvariable=self._amount, width=12)
        amount_entry.grid(row=1, column=4, padx=(0, 8))
        ttk.Button(form, text="Ajouter", command=lambda: call(self._get, "on_add")).grid(row=1, column=5)
        for entry in (self._label_entry, amount_entry):
            entry.bind("<Return>", lambda _e: call(self._get, "on_add"))

        self._title = ttk.Label(parent, text="", font=("Arial", 11, "bold"))
        self._title.pack(anchor="w", pady=(12, 4))
        self._table = Table(parent, [Column("category", "Catégorie", 140), Column("kind", "Type", 90),
                                     Column("label", "Libellé", 320), Column("amount", "Montant", 120, "e")],
                            height=12)
        ttk.Button(parent, text="Supprimer la sélection",
                   command=lambda: call(self._get, "on_delete")).pack(anchor="e", pady=(6, 0))

        self._date.trace_add("write", lambda *_: call(self._get, "on_date_changed"))

    def _get(self):
        return self._listener

    def set_listener(self, listener: TransactionsListener) -> None:
        self._listener = listener

    def set_categories(self, categories: Sequence[str]) -> None:
        self._combo["values"] = list(categories)

    def get_category(self) -> str:
        return self._category.get()

    def set_category(self, name: str) -> None:
        self._category.set(name)

    def get_form(self) -> TransactionForm:
        return TransactionForm(self._date.get(), self._category.get(), self._kind.get(),
                               self._label.get(), self._amount.get())

    def get_date_text(self) -> str:
        return self._date.get()

    def clear_entry(self) -> None:
        self._label.set("")
        self._amount.set("")
        self._label_entry.focus_set()

    def show_day(self, title: str, rows: Sequence[Row]) -> None:
        self._title.config(text=title)
        self._table.show(rows)

    def get_selected_ids(self) -> list[str]:
        return self._table.selected_ids()
