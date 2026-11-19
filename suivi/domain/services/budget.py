"""Planification du budget par catégorie (Python pur)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..model.ledger import Ledger
from ..model.period import Period


@dataclass(frozen=True)
class BudgetLine:
    category: str
    daily: int          # budget par jour de la catégorie
    days: int
    needed: int         # daily x days
    balance: int        # solde disponible de la catégorie avant le début de la période
    suggestion: int     # max(0, needed - balance)


class BudgetPlanner:
    def propose(self, ledger: Ledger, period: Period) -> list[BudgetLine]:
        balance: dict = defaultdict(int)
        for t in ledger.transactions:
            if t.date < period.start:
                balance[t.category] += t.signed_amount
        lines = []
        for category in ledger.categories:
            daily = ledger.daily_budget(category)
            needed = daily * period.days
            lines.append(BudgetLine(category, daily, period.days, needed, balance[category],
                                    max(0, needed - balance[category])))
        return lines

    @staticmethod
    def deposit_label(period: Period) -> str:
        return f"Budget du {period.start:%d/%m/%Y} au {period.end:%d/%m/%Y}"
