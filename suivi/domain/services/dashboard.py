"""Indicateurs du tableau de bord : soldes restants par budget et flux d'argent par jour (Python pur)."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from ..model.ledger import Ledger
from ..model.period import Period
from ..model.transaction import Kind


@dataclass(frozen=True)
class BudgetShare:
    category: str
    balance: int        # dépôts - dépenses de la catégorie (toujours > 0 ici)
    share: float        # part du total des soldes positifs, en %


@dataclass(frozen=True)
class BudgetShares:
    items: tuple[BudgetShare, ...]                 # soldes positifs, du plus grand au plus petit
    total: int                                     # somme des soldes positifs
    deficits: tuple[tuple[str, int], ...]          # catégories dont les dépenses dépassent les dépôts : (nom, montant > 0)

    @property
    def deficit_total(self) -> int:
        return sum(amount for _c, amount in self.deficits)


@dataclass(frozen=True)
class DayFlow:
    date: dt.date
    deposits: int
    expenses: int


@dataclass(frozen=True)
class FlowSeries:
    period: Period
    days: tuple[DayFlow, ...]                      # un élément pour CHAQUE jour de la période (zéros compris)
    total_deposits: int
    total_expenses: int
    peak_expense_day: Optional[DayFlow]            # jour de plus forte sortie (None s'il n'y en a aucune)
    peak_expense_breakdown: tuple[tuple[str, int], ...]   # ce jour-là : (catégorie, dépense), du plus grand au plus petit
    peak_deposit_day: Optional[DayFlow]


class DashboardAnalyzer:
    def budget_shares(self, ledger: Ledger) -> BudgetShares:
        balances: dict = defaultdict(int)
        for t in ledger.transactions:
            balances[t.category] += t.signed_amount
        positive = sorted(((c, b) for c, b in balances.items() if b > 0), key=lambda cb: (-cb[1], cb[0]))
        total = sum(b for _c, b in positive)
        items = tuple(BudgetShare(c, b, round(b / total * 100, 1)) for c, b in positive)
        deficits = tuple(sorted(((c, -b) for c, b in balances.items() if b < 0), key=lambda cb: (-cb[1], cb[0])))
        return BudgetShares(items, total, deficits)

    def flows(self, ledger: Ledger, period: Period) -> FlowSeries:
        deposits = {day: 0 for day in period.each_day()}
        expenses = dict(deposits)
        by_category: dict = defaultdict(lambda: defaultdict(int))     # jour -> catégorie -> dépense
        for t in ledger.transactions:
            if not period.contains(t.date):
                continue
            if t.kind is Kind.DEPOSIT:
                deposits[t.date] += t.amount
            else:
                expenses[t.date] += t.amount
                by_category[t.date][t.category] += t.amount
        days = tuple(DayFlow(d, deposits[d], expenses[d]) for d in deposits)
        peak_expense = max((d for d in days if d.expenses > 0), key=lambda d: d.expenses, default=None)
        peak_deposit = max((d for d in days if d.deposits > 0), key=lambda d: d.deposits, default=None)
        breakdown = ()
        if peak_expense is not None:
            breakdown = tuple(sorted(by_category[peak_expense.date].items(), key=lambda kv: (-kv[1], kv[0])))
        return FlowSeries(period, days, sum(deposits.values()), sum(expenses.values()), peak_expense,
                          breakdown, peak_deposit)
