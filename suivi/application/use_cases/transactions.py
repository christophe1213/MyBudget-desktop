from __future__ import annotations

import datetime as dt

from ...domain.model.transaction import Kind, Transaction
from ...domain.services.balances import BalanceCalculator
from ..ports.inbound import ManageTransactions
from ..session import LedgerSession


class TransactionsUseCase(ManageTransactions):
    def __init__(self, session: LedgerSession, balances: BalanceCalculator):
        self._session = session
        self._balances = balances

    def categories(self) -> list[str]:
        return self._session.ledger.categories

    def transactions_on(self, day: dt.date) -> list[tuple[int, Transaction]]:
        return self._session.ledger.transactions_on(day)

    def balance_at(self, day: dt.date) -> int:
        return self._balances.at(self._session.ledger, day)

    def add(self, day: dt.date, category: str, kind: Kind, label: str, amount: int) -> None:
        self._session.apply(lambda ledger: ledger.add_transaction(day, category, kind, label, amount))

    def delete(self, ids: list[int]) -> None:
        self._session.apply(lambda ledger: ledger.remove_transactions(ids))
