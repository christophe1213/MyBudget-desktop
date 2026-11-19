"""Rapport de période : sommes des dépôts et des dépenses par catégorie (Python pur)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..model.ledger import Ledger
from ..model.period import Period
from ..model.transaction import Kind


@dataclass(frozen=True)
class CategoryTotals:
    category: str
    deposits: int
    expenses: int
    net: int
    expense_share: float   # part des dépenses totales, en %
    count: int


@dataclass(frozen=True)
class ExpenseItem:
    category: str
    label: str
    amount: int


@dataclass(frozen=True)
class Report:
    period: Period
    opening_balance: int
    closing_balance: int
    total_deposits: int
    total_expenses: int
    net: int
    average_daily_expense: int
    transaction_count: int
    categories: tuple[CategoryTotals, ...]
    top_expenses: tuple[ExpenseItem, ...]


class ReportBuilder:
    TOP_SIZE = 10

    def build(self, ledger: Ledger, period: Period) -> Report:
        opening = ledger.initial_balance + sum(t.signed_amount for t in ledger.transactions
                                               if t.date < period.start)
        totals: dict = defaultdict(lambda: [0, 0, 0])   # dépôts, dépenses, nombre
        by_label: dict = defaultdict(int)
        for t in ledger.transactions:
            if not period.contains(t.date):
                continue
            row = totals[t.category]
            row[0 if t.kind is Kind.DEPOSIT else 1] += t.amount
            row[2] += 1
            if t.kind is Kind.EXPENSE:
                by_label[(t.category, t.label)] += t.amount

        total_expenses = sum(row[1] for row in totals.values())
        total_deposits = sum(row[0] for row in totals.values())
        categories = tuple(
            CategoryTotals(c, dep, exp, dep - exp,
                           round(exp / total_expenses * 100, 1) if total_expenses else 0.0, n)
            for c, (dep, exp, n) in sorted(totals.items(), key=lambda kv: (-kv[1][1], kv[0])))
        top = tuple(ExpenseItem(c, label, amount) for (c, label), amount in
                    sorted(by_label.items(), key=lambda kv: (-kv[1], kv[0]))[:self.TOP_SIZE])
        net = total_deposits - total_expenses
        return Report(period, opening, opening + net, total_deposits, total_expenses, net,
                      round(total_expenses / period.days), sum(row[2] for row in totals.values()),
                      categories, top)
