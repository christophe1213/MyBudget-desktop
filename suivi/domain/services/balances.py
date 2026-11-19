"""Calcul des soldes (Python pur)."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass

from ..model.ledger import Ledger
from ..model.transaction import Kind


@dataclass(frozen=True)
class DayBalance:
    date: dt.date
    deposits: int
    expenses: int
    balance: int          # solde en fin de journée


@dataclass(frozen=True)
class CategoryBalance:
    date: dt.date
    category: str
    deposits: int
    expenses: int
    net: int
    balance: int          # dépôts - dépenses cumulés de la catégorie (le solde initial n'en fait pas partie)


class BalanceCalculator:
    def by_date(self, ledger: Ledger) -> list[DayBalance]:
        flows: dict = defaultdict(lambda: [0, 0])
        for t in ledger.transactions:
            flows[t.date][0 if t.kind is Kind.DEPOSIT else 1] += t.amount
        balance, result = ledger.initial_balance, []
        for day in sorted(flows):
            deposits, expenses = flows[day]
            balance += deposits - expenses
            result.append(DayBalance(day, deposits, expenses, balance))
        return result

    def at(self, ledger: Ledger, day: dt.date) -> int:
        """Solde à la fin du jour donné (toutes les transactions jusqu'à ce jour comprises)."""
        return ledger.initial_balance + sum(t.signed_amount for t in ledger.transactions if t.date <= day)

    def total(self, ledger: Ledger) -> int:
        return ledger.initial_balance + sum(t.signed_amount for t in ledger.transactions)

    def by_category(self, ledger: Ledger) -> list[CategoryBalance]:
        flows: dict = defaultdict(lambda: [0, 0])
        for t in ledger.transactions:
            flows[(t.category, t.date)][0 if t.kind is Kind.DEPOSIT else 1] += t.amount
        running: dict = defaultdict(int)
        rows = []
        for (category, day) in sorted(flows):
            deposits, expenses = flows[(category, day)]
            running[category] += deposits - expenses
            rows.append(CategoryBalance(day, category, deposits, expenses, deposits - expenses,
                                        running[category]))
        return sorted(rows, key=lambda r: (r.date, r.category))
