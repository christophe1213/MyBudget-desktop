"""Page « Tableau de bord » : camembert des budgets restants et courbes des entrées / sorties."""
from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from ..contract.dto import FlowChartData, PieData
from ..contract.interfaces import DashboardListener, DashboardView
from ..dashboard_painter import FlowPainter, PiePainter
from .chart import DASHBOARD_PALETTE, PainterCanvas
from .widgets import button, call, card, entry, label


class CtkDashboardView(DashboardView):
    def __init__(self, parent):
        self._listener: Optional[DashboardListener] = None
        self._start = ctk.StringVar()
        self._end = ctk.StringVar()

        parent.grid_columnconfigure(0, weight=2, uniform="dashboard")
        parent.grid_columnconfigure(1, weight=3, uniform="dashboard")
        parent.grid_rowconfigure(0, weight=1)

        # ---- carte de gauche : camembert ------------------------------------------------------------
        left = card(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        label(left, "Répartition des budgets restants", "heading").pack(anchor="w", padx=20, pady=(18, 4))
        self._pie = PainterCanvas(left, PiePainter(DASHBOARD_PALETTE), 300)
        self._pie_note = label(left, "", "muted", wraplength=360)
        self._pie_note.pack(anchor="w", padx=20, pady=(4, 18))

        # ---- carte de droite : entrées et sorties selon les dates ---------------------------------------
        right = card(parent)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        header = ctk.CTkFrame(right, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))
        label(header, "Entrées et sorties selon les dates", "heading").pack(side="left")
        for text, days in (("Tout", None), ("30 j", 30), ("7 j", 7)):
            small = button(header, text, lambda d=days: call(self._get, "on_preset", d), "secondary", 58)
            small.configure(height=30)
            small.pack(side="right", padx=(6, 0))

        period = ctk.CTkFrame(right, fg_color="transparent")
        period.pack(fill="x", padx=20, pady=(0, 4))
        label(period, "Du", "muted").pack(side="left", padx=(0, 6))
        self._entry(period, self._start)
        label(period, "au", "muted").pack(side="left", padx=(12, 6))
        self._entry(period, self._end)
        apply = button(period, "Appliquer", lambda: call(self._get, "on_apply_filter"), "primary", 100)
        apply.configure(height=32)
        apply.pack(side="left", padx=(12, 0))

        self._flow = PainterCanvas(right, FlowPainter(DASHBOARD_PALETTE), 300)
        self._flow_note = label(right, "", "muted", wraplength=520)
        self._flow_note.pack(anchor="w", padx=20, pady=(4, 18))

    def _entry(self, parent, variable) -> None:
        field = entry(parent, variable, 112)
        field.configure(height=32)
        field.bind("<Return>", lambda _e: call(self._get, "on_apply_filter"))
        field.pack(side="left")

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
        self._pie_note.configure(text=data.note if data else
                                 "Les soldes restants de vos budgets apparaîtront ici dès qu'ils seront positifs.")

    def show_flows(self, data: Optional[FlowChartData]) -> None:
        self._flow.draw(data)
        self._flow_note.configure(text=data.note if data else "")
