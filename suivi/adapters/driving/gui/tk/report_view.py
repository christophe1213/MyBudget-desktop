"""Onglet « Rapport » : totaux par catégorie entre deux dates."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence

from ..contract.dto import Row
from ..contract.interfaces import ReportListener, ReportView
from .widgets import Column, Table, call


class TkReportView(ReportView):
    def __init__(self, parent):
        self._listener: Optional[ReportListener] = None
        self._start = tk.StringVar()
        self._end = tk.StringVar()

        top = ttk.LabelFrame(parent, text="Période analysée", padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Du").pack(side="left")
        ttk.Entry(top, textvariable=self._start, width=12).pack(side="left", padx=(4, 10))
        ttk.Label(top, text="au").pack(side="left")
        ttk.Entry(top, textvariable=self._end, width=12).pack(side="left", padx=(4, 10))
        ttk.Label(top, text="(JJ/MM/AAAA, dates incluses)", foreground="#555").pack(side="left", padx=(0, 10))
        ttk.Button(top, text="Générer le rapport", command=lambda: call(self._get, "on_generate")).pack(
            side="left")
        ttk.Button(top, text="Exporter en Excel", command=lambda: call(self._get, "on_export")).pack(
            side="left", padx=6)

        self._summary = ttk.Label(parent, text="", justify="left", font=("Arial", 10))
        self._summary.pack(anchor="w", pady=(10, 6))
        self._table = Table(parent, [Column("category", "Catégorie", 170),
                                     Column("deposits", "Total dépôts", 130, "e"),
                                     Column("expenses", "Total dépenses", 130, "e"),
                                     Column("net", "Net", 130, "e"),
                                     Column("share", "Part des dépenses", 130, "e"),
                                     Column("count", "Nb transactions", 120, "e")])

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
        self._summary.config(text=summary_text)
        self._table.show(rows)

    def reset(self, message: str) -> None:
        self._summary.config(text=message)
        self._table.show([])
