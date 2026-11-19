from __future__ import annotations

from ...domain.model.period import Period
from ...domain.services.spending import SpendingAnalysis, SpendingAnalyzer, SpendingStats
from ..ports.inbound import AnalyzeSpending
from ..ports.outbound import Clock
from ..session import LedgerSession


class AnalysisUseCase(AnalyzeSpending):
    def __init__(self, session: LedgerSession, analyzer: SpendingAnalyzer, clock: Clock):
        self._session = session
        self._analyzer = analyzer
        self._clock = clock

    def categories(self) -> list[str]:
        return self._session.ledger.categories

    def default_period(self) -> Period:
        data_range = self._session.ledger.date_range()
        start, end = data_range if data_range else (self._clock.today(),) * 2
        return Period(start, end)

    def analyze(self, category: str, period: Period) -> SpendingAnalysis:
        return self._analyzer.analyze(self._session.ledger, category, period)

    def diagnose(self, stats: SpendingStats) -> str:
        return self._analyzer.diagnose(stats)

    def daily_budget(self, category: str) -> int:
        return self._session.ledger.daily_budget(category)
