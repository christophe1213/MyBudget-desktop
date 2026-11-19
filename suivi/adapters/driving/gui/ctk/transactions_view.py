"""Page « Saisie »."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

import customtkinter as ctk

from .....domain.model.transaction import Kind
from ..contract.dto import Row, TransactionForm
from ..contract.interfaces import TransactionsListener, TransactionsView
from .widgets import Column, Table, button, call, card, combo, entry, field, label, segmented

KINDS = tuple(k.value for k in Kind)


class CtkTransactionsView(TransactionsView):
    def __init__(self, parent):
        self._listener: Optional[TransactionsListener] = None
        self._date = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self._category = ctk.StringVar()
        self._kind = ctk.StringVar(value=KINDS[0])
        self._label = ctk.StringVar()
        self._amount = ctk.StringVar()

        form = card(parent)
        form.pack(fill="x")
        label(form, "Nouvelle transaction", "section").pack(anchor="w", padx=20, pady=(16, 10))
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        for caption, build in [
            ("Date", lambda p: entry(p, self._date, 120)),
            ("Catégorie", lambda p: self._build_category(p)),
            ("Type", lambda p: segmented(p, self._kind, KINDS, 200)),
            ("Libellé", lambda p: self._build_label(p)),
            ("Montant (Ar)", lambda p: self._build_amount(p)),
        ]:
            column = field(row, caption)
            column.pack(side="left", padx=(0, 14))
            build(column).pack(anchor="w")
        button(row, "Ajouter", lambda: call(self._get, "on_add"), "primary", 110).pack(side="left", pady=(22, 0))

        self._title = label(parent, "", "strong")
        self._title.pack(anchor="w", pady=(18, 8))
        self._table = Table(parent, [Column("category", "Catégorie", 150), Column("kind", "Type", 100),
                                     Column("label", "Libellé", 340), Column("amount", "Montant", 140, "e")],
                            height=10)
        button(parent, "Supprimer la sélection", lambda: call(self._get, "on_delete"), "danger").pack(
            anchor="e", pady=(10, 0))
        self._date.trace_add("write", lambda *_: call(self._get, "on_date_changed"))

    def _build_category(self, parent):
        self._combo = combo(parent, self._category, 170)
        return self._combo

    def _build_label(self, parent):
        self._label_entry = entry(parent, self._label, 260)
        self._label_entry.bind("<Return>", lambda _e: call(self._get, "on_add"))
        return self._label_entry

    def _build_amount(self, parent):
        widget = entry(parent, self._amount, 130)
        widget.bind("<Return>", lambda _e: call(self._get, "on_add"))
        return widget

    def _get(self):
        return self._listener

    def set_listener(self, listener: TransactionsListener) -> None:
        self._listener = listener

    def set_categories(self, categories: Sequence[str]) -> None:
        self._combo.configure(values=list(categories))

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
        self._title.configure(text=title)
        self._table.show(rows)

    def get_selected_ids(self) -> list[str]:
        return self._table.selected_ids()
