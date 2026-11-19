from __future__ import annotations

from typing import Optional

from .....application.ports.inbound import EventSource, ManageCategories, PlanBudgets
from .....domain.model.period import Period
from .....domain.services.budget import BudgetLine
from ..contract.dto import Row
from ..contract.interfaces import BudgetListener, BudgetView, Dialogs
from ..formatting import format_ar, format_date
from ..parsing import parse_date
from .base import Controller

_PLACEHOLDER = "Choisissez la période puis cliquez sur « Calculer les suggestions »."


class BudgetController(Controller, BudgetListener):
    """Onglet « Budget » : suggestion = budget/jour x nb de jours - solde de la catégorie,
    montant retenu ajustable, puis création d'un dépôt par catégorie."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: BudgetView, budgets: PlanBudgets,
                 categories: ManageCategories):
        super().__init__(events, dialogs)
        self._view = view
        self._budgets = budgets
        self._categories = categories
        self._lines: list[BudgetLine] = []
        self._retained: dict[str, int] = {}
        self._period: Optional[Period] = None
        self._period_ready = False
        view.set_listener(self)

    # ---- cycle de vie -------------------------------------------------------------------------
    def reset(self) -> None:
        self._period_ready = False

    def refresh(self) -> None:
        if not self._period_ready:
            period = self._budgets.default_period()
            self._view.set_period(format_date(period.start), format_date(period.end))
            self._period_ready = True
        self._clear()

    def on_budgets_changed(self) -> None:
        self._clear()  # un budget par jour a changé : les suggestions sont périmées

    def _clear(self) -> None:
        self._lines, self._retained, self._period = [], {}, None
        self._view.clear_proposal(_PLACEHOLDER)

    # ---- actions ---------------------------------------------------------------------------------
    def on_calculate(self) -> None:
        self._calculate()

    def _calculate(self, keep: Optional[dict] = None) -> None:
        with self.guard("Budget"):
            start, end = (parse_date(t) for t in self._view.get_period())
            period = Period(start, end)
            lines = self._budgets.propose(period)
            if not lines:
                self._dialogs.info("Budget", "Ajoutez d'abord des catégories (onglet « Catégories »).")
                return
            keep = keep or {}
            self._lines, self._period = lines, period
            self._retained = {line.category: keep.get(line.category, line.suggestion) for line in lines}
            self._show()

    def _show(self, selected_id: Optional[str] = None) -> None:
        period = self._period
        rows = [Row(str(i), (line.category, format_ar(line.daily), format_ar(line.needed),
                             format_ar(line.balance), format_ar(line.suggestion),
                             format_ar(self._retained[line.category])))
                for i, line in enumerate(self._lines)]
        text = (f"Période : {format_date(period.start)} au {format_date(period.end)} ({period.days} jours)\n"
                f"Total des suggestions : {format_ar(sum(line.suggestion for line in self._lines))}      "
                f"Total retenu : {format_ar(sum(self._retained.values()))}")
        if not self._categories.has_daily_budgets():
            text += ("\nAucun budget par jour défini : sélectionnez une catégorie "
                     "puis « Modifier le budget / jour… ».")
        self._view.show_proposal(text, rows, selected_id)

    def _selected(self, interactive: bool):
        selected = self._view.get_selected_id()
        if not self._lines or selected is None:
            if interactive:
                self._dialogs.info("Budget", "Calculez les suggestions puis sélectionnez une catégorie.")
            return None
        return selected, self._lines[int(selected)]

    def on_adjust_retained(self, interactive: bool = True) -> None:
        choice = self._selected(interactive)
        if choice is None:
            return
        selected, line = choice
        value = self._dialogs.ask_int(
            "Montant retenu",
            f"{line.category} — suggestion : {format_ar(line.suggestion)}\nMontant à déposer (Ar) :",
            self._retained[line.category], 0)
        if value is None:
            return
        self._retained[line.category] = int(value)
        self._show(selected)

    def on_change_daily(self) -> None:
        choice = self._selected(True)
        if choice is None:
            return
        _selected, line = choice
        value = self._dialogs.ask_int("Budget par jour", f"Budget par jour pour « {line.category} » (Ar) :",
                                      line.daily, 0)
        if value is None:
            return
        keep = {c: m for c, m in self._retained.items() if c != line.category}  # montants déjà ajustés
        with self.guard("Budget"):
            self._categories.set_daily_budget(line.category, int(value))
            self._calculate(keep)

    def on_validate(self) -> None:
        if self._period is None:
            self._dialogs.info("Budget", "Calculez d'abord les suggestions.")
            return
        period = self._period
        lines = [(c, m) for c, m in self._retained.items() if m > 0]
        if not lines:
            self._dialogs.info("Budget", "Tous les montants retenus sont à 0 : aucun dépôt à créer.")
            return
        total = sum(m for _c, m in lines)
        label = self._budgets.deposit_label(period)
        if not self._dialogs.confirm(
                "Valider le budget",
                f"Créer {len(lines)} dépôt(s) pour un total de {format_ar(total)} ?\n"
                f"Date des dépôts : {format_date(period.start)}\nLibellé : {label}"):
            return
        already = self._budgets.categories_with_deposit([c for c, _m in lines], label)
        if already and not self._dialogs.confirm(
                "Budget déjà validé",
                f"Un dépôt « {label} » existe déjà pour : {', '.join(already)}.\nAjouter quand même ?"):
            return
        with self.guard("Budget"):
            created = self._budgets.create_deposits(period, lines)
            self._dialogs.info("Budget", f"{created} dépôt(s) créé(s) pour un total de {format_ar(total)}.")
