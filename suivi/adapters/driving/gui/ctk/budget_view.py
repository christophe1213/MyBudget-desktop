"""Page « Budget » : budget par catégorie sur une période, ajustable, puis dépôts."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from ..contract.interfaces import BudgetListener, BudgetView
from .widgets import Column, Table, button, call, card, entry, field, label, tinted


class CtkBudgetView(BudgetView):
    def __init__(self, parent):
        self._listener: Optional[BudgetListener] = None
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
        button(row, "Calculer les suggestions", lambda: call(self._get, "on_calculate"), "primary", 200).pack(
            side="left", pady=(22, 0))

        box = tinted(parent)
        box.pack(fill="x", pady=14)
        self._summary = label(box, "", "kpi", wraplength=1000)
        self._summary.pack(anchor="w", padx=16, pady=12)
        self._table = Table(parent, [Column("category", "Catégorie", 170), Column("daily", "Budget / jour", 130, "e"),
                                     Column("need", "Budget de la période", 170, "e"),
                                     Column("balance", "Solde disponible", 150, "e"),
                                     Column("suggestion", "Suggestion", 130, "e"),
                                     Column("retained", "Montant retenu", 140, "e")])
        self._table.on_double_click(self._double_click)

        buttons = ctk.CTkFrame(parent, fg_color="transparent")
        buttons.pack(fill="x", pady=(12, 0))
        button(buttons, "Ajuster le montant retenu…", lambda: call(self._get, "on_adjust_retained"),
               "secondary").pack(side="left")
        button(buttons, "Modifier le budget / jour…", lambda: call(self._get, "on_change_daily"),
               "secondary").pack(side="left", padx=10)
        button(buttons, "Valider et créer les dépôts", lambda: call(self._get, "on_validate"), "primary").pack(
            side="right")
        label(parent, "Suggestion = budget par jour × nombre de jours − solde disponible de la catégorie avant "
                      "la date de début (jamais négative). Double-clic sur une ligne pour ajuster le montant "
                      "retenu ; 0 = aucun dépôt. Les dépôts sont datés du premier jour de la période.",
              "muted", wraplength=1000).pack(anchor="w", pady=(10, 0))

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

    def show_proposal(self, summary_text: str, rows: Sequence[Row], selected_id: Optional[str] = None) -> None:
        self._summary.configure(text=summary_text)
        self._table.show(rows, selected_id)

    def clear_proposal(self, message: str) -> None:
        self._summary.configure(text=message)
        self._table.show([])

    def get_selected_id(self) -> Optional[str]:
        return self._table.selected_id()
