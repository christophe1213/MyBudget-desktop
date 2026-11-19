"""Page « Rapport » : totaux par catégorie entre deux dates."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from ..contract.interfaces import ReportListener, ReportView
from .widgets import Column, Table, button, call, card, entry, field, label, tinted


class CtkReportView(ReportView):
    def __init__(self, parent):
        self._listener: Optional[ReportListener] = None
        self._start = ctk.StringVar()
        self._end = ctk.StringVar()

        top = card(parent)
        top.pack(fill="x")
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)
        for caption, var in (("Du (JJ/MM/AAAA)", self._start), ("Au (inclus)", self._end)):
            column = field(row, caption)
            column.pack(side="left", padx=(0, 14))
            entry(column, var, 130).pack(anchor="w")
        button(row, "Générer le rapport", lambda: call(self._get, "on_generate"), "primary", 160).pack(
            side="left", pady=(22, 0))
        button(row, "Exporter", lambda: call(self._get, "on_export"), "secondary", 110).pack(
            side="left", padx=10, pady=(22, 0))

        box = tinted(parent)
        box.pack(fill="x", pady=14)
        self._summary = label(box, "", "kpi", wraplength=1000)
        self._summary.pack(anchor="w", padx=16, pady=12)
        self._table = Table(parent, [Column("category", "Catégorie", 190), Column("deposits", "Total dépôts", 140, "e"),
                                     Column("expenses", "Total dépenses", 140, "e"), Column("net", "Net", 140, "e"),
                                     Column("share", "Part des dépenses", 140, "e"),
                                     Column("count", "Transactions", 120, "e")])

    def _get(self):
        return self._listener

    def set_listener(self, listener: ReportListener) -> None:
        self._listener = listener

    def get_period(self) -> tuple[str, str]:
        return self._start.get(), self._end.get()

    def set_period(self, start: str, end: str) -> None:
        self._start.set(start)
        self._end.set(end)

    def show_report(self, summary_text: str, rows: Sequence[Row]) -> None:
        self._summary.configure(text=summary_text)
        self._table.show(rows)

    def reset(self, message: str) -> None:
        self._summary.configure(text=message)
        self._table.show([])
