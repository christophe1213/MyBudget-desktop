"""Onglet « Tableau de bord » (interface classique) : mêmes graphiques que l'interface customtkinter."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..contract.dto import FlowChartData, PieData
from ..contract.interfaces import DashboardListener, DashboardView
from ..dashboard_painter import FlowPainter, PiePainter
from ..view_support import call
from .chart import PainterCanvas


class TkDashboardView(DashboardView):
    def __init__(self, parent):
        self._listener: Optional[DashboardListener] = None
        self._start = tk.StringVar()
        self._end = tk.StringVar()
        parent.columnconfigure(0, weight=2, uniform="dashboard")
        parent.columnconfigure(1, weight=3, uniform="dashboard")
        parent.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(parent, text="Répartition des budgets restants", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._pie = PainterCanvas(left, PiePainter(), 300)
        self._pie_note = ttk.Label(left, text="", wraplength=330, foreground="#555")
        self._pie_note.pack(anchor="w", pady=(6, 0))

        right = ttk.LabelFrame(parent, text="Entrées et sorties selon les dates", padding=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Label(bar, text="Du").pack(side="left")
        ttk.Entry(bar, textvariable=self._start, width=11).pack(side="left", padx=(4, 8))
        ttk.Label(bar, text="au").pack(side="left")
        ttk.Entry(bar, textvariable=self._end, width=11).pack(side="left", padx=(4, 8))
        ttk.Button(bar, text="Appliquer", command=lambda: call(self._get, "on_apply_filter")).pack(side="left")
        for text, days in (("Tout", None), ("30 j", 30), ("7 j", 7)):
            ttk.Button(bar, text=text, width=5, command=lambda d=days: call(self._get, "on_preset", d)).pack(
                side="right", padx=(4, 0))
        self._flow = PainterCanvas(right, FlowPainter(), 300)
        self._flow_note = ttk.Label(right, text="", wraplength=480, foreground="#555")
        self._flow_note.pack(anchor="w", pady=(6, 0))

    def _get(self):
        return self._listener

    def set_listener(self, listener: DashboardListener) -> None:
        self._listener = listener

    def get_period(self) -> tuple[str, str]:
        return self._start.get(), self._end.get()

    def set_period(self, start: str, end: str) -> None:
        self._start.set(start)
        self._end.set(end)

    def show_budget_shares(self, data: Optional[PieData]) -> None:
        self._pie.draw(data)
        self._pie_note.config(text=data.note if data else "Les soldes restants apparaîtront ici dès qu'ils seront positifs.")

    def show_flows(self, data: Optional[FlowChartData]) -> None:
        self._flow.draw(data)
        self._flow_note.config(text=data.note if data else "")
