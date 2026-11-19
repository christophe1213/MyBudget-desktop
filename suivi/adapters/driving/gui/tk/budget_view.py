"""Onglet « Budget » : budget par catégorie sur une période, ajustable, puis dépôts."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence

from ..contract.dto import Row
from ..contract.interfaces import BudgetListener, BudgetView
from .widgets import Column, Table, call


class TkBudgetView(BudgetView):
    def __init__(self, parent):
        self._listener: Optional[BudgetListener] = None
        self._start = tk.StringVar()
        self._end = tk.StringVar()

        top = ttk.LabelFrame(parent, text="Période à budgétiser", padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Du").pack(side="left")
        ttk.Entry(top, textvariable=self._start, width=12).pack(side="left", padx=(4, 10))
        ttk.Label(top, text="au").pack(side="left")
        ttk.Entry(top, textvariable=self._end, width=12).pack(side="left", padx=(4, 10))
        ttk.Label(top, text="(JJ/MM/AAAA, dates incluses)", foreground="#555").pack(side="left", padx=(0, 10))
        ttk.Button(top, text="Calculer les suggestions", command=lambda: call(self._get, "on_calculate")).pack(
            side="left")

        self._summary = ttk.Label(parent, text="", justify="left", font=("Arial", 10))
        self._summary.pack(anchor="w", pady=(10, 6))
        self._table = Table(parent, [Column("category", "Catégorie", 150),
                                     Column("daily", "Budget / jour", 110, "e"),
                                     Column("need", "Budget de la période", 150, "e"),
                                     Column("balance", "Solde disponible", 140, "e"),
                                     Column("suggestion", "Suggestion", 120, "e"),
                                     Column("retained", "Montant retenu", 130, "e")])
        self._table.on_double_click(self._double_click)

        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Ajuster le montant retenu…",
                   command=lambda: call(self._get, "on_adjust_retained")).pack(side="left")
        ttk.Button(buttons, text="Modifier le budget / jour…",
                   command=lambda: call(self._get, "on_change_daily")).pack(side="left", padx=6)
        ttk.Button(buttons, text="Valider et créer les dépôts",
                   command=lambda: call(self._get, "on_validate")).pack(side="right")
        ttk.Label(parent, foreground="#555", wraplength=900, justify="left",
                  text="Suggestion = budget par jour × nombre de jours − solde disponible de la catégorie "
                       "avant la date de début (jamais négative). Le montant retenu est librement ajustable "
                       "(double-clic sur une ligne) ; 0 = aucun dépôt pour cette catégorie. "
                       "Les dépôts sont datés du premier jour de la période.").pack(anchor="w", pady=(6, 0))

    def _get(self):
        return self._listener

    def _double_click(self) -> None:
        if self._table.selected_id() is not None:
            call(self._get, "on_adjust_retained", False)

    def set_listener(self, listener: BudgetListener) -> None:
        self._listener = listener

    def get_period(self) -> tuple[str, str]:
        return self._start.get(), self._end.get()

    def set_period(self, start: str, end: str) -> None:
        self._start.set(start)
        self._end.set(end)

    def show_proposal(self, summary_text: str, rows: Sequence[Row],
                      selected_id: Optional[str] = None) -> None:
        self._summary.config(text=summary_text)
        self._table.show(rows, selected_id)

    def clear_proposal(self, message: str) -> None:
        self._summary.config(text=message)
        self._table.show([])

    def get_selected_id(self) -> Optional[str]:
        return self._table.selected_id()
