from __future__ import annotations

import datetime as dt

from ...domain.services.balances import BalanceCalculator, CategoryBalance, DayBalance
from ..ports.inbound import QueryBalances
from ..session import LedgerSession


class BalancesUseCase(QueryBalances):
    def __init__(self, session: LedgerSession, balances: BalanceCalculator):
        self._session = session
        self._balances = balances

    def categories(self) -> list[str]:
        return self._session.ledger.categories

    def transaction_dates(self) -> list[dt.date]:
        return sorted({t.date for t in self._session.ledger.transactions})

    def balance_by_date(self) -> list[DayBalance]:
        return self._balances.by_date(self._session.ledger)

    def category_balances(self) -> list[CategoryBalance]:
        return self._balances.by_category(self._session.ledger)
