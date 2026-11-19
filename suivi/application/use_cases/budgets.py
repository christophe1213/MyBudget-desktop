from __future__ import annotations

import datetime as dt
from typing import Iterable

from ...domain.model.period import Period
from ...domain.services.budget import BudgetLine, BudgetPlanner
from ..ports.inbound import PlanBudgets
from ..ports.outbound import Clock
from ..session import LedgerSession


class BudgetsUseCase(PlanBudgets):
    """Budget = budget/jour × nombre de jours − solde de la catégorie ; puis création des dépôts."""

    def __init__(self, session: LedgerSession, planner: BudgetPlanner, clock: Clock):
        self._session = session
        self._planner = planner
        self._clock = clock

    def default_period(self) -> Period:
        """7 jours à partir du lendemain de la dernière transaction (ou d'aujourd'hui s'il n'y en a pas)."""
        data_range = self._session.ledger.date_range()
        start = data_range[1] + dt.timedelta(days=1) if data_range else self._clock.today()
        return Period(start, start + dt.timedelta(days=6))

    def propose(self, period: Period) -> list[BudgetLine]:
        return self._planner.propose(self._session.ledger, period)

    def deposit_label(self, period: Period) -> str:
        return self._planner.deposit_label(period)

    def categories_with_deposit(self, categories: Iterable[str], label: str) -> list[str]:
        return self._session.ledger.categories_with_deposit(categories, label)

    def create_deposits(self, period: Period, lines: list[tuple[str, int]]) -> int:
        label = self._planner.deposit_label(period)
        return self._session.apply(lambda ledger: ledger.add_deposits(lines, period.start, label))
