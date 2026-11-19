from __future__ import annotations

import datetime as dt
from typing import Optional

from ...domain.model.period import Period
from ...domain.services.dashboard import BudgetShares, DashboardAnalyzer, FlowSeries
from ..ports.inbound import ViewDashboard
from ..ports.outbound import Clock
from ..session import LedgerSession

DEFAULT_DAYS = 14   # fenêtre proposée par défaut pour le graphique des flux


class DashboardUseCase(ViewDashboard):
    def __init__(self, session: LedgerSession, analyzer: DashboardAnalyzer, clock: Clock):
        self._session = session
        self._analyzer = analyzer
        self._clock = clock

    def budget_shares(self) -> BudgetShares:
        return self._analyzer.budget_shares(self._session.ledger)

    def data_period(self) -> Optional[Period]:
        data_range = self._session.ledger.date_range()
        return Period(*data_range) if data_range else None

    def default_period(self) -> Period:
        """Les 14 derniers jours de données (ou toute la période si elle est plus courte)."""
        data = self.data_period()
        if data is None:
            return Period(self._clock.today(), self._clock.today())
        return Period(max(data.start, data.end - dt.timedelta(days=DEFAULT_DAYS - 1)), data.end)

    def flows(self, period: Period) -> FlowSeries:
        return self._analyzer.flows(self._session.ledger, period)
