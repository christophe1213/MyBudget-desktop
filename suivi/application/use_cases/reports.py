from __future__ import annotations

from ...domain.model.period import Period
from ...domain.services.reports import Report, ReportBuilder
from ..naming import slug
from ..ports.inbound import BuildReports, ManageWallets
from ..ports.outbound import Clock, FileOpener, ReportExporter
from ..session import LedgerSession


class ReportsUseCase(BuildReports):
    def __init__(self, session: LedgerSession, builder: ReportBuilder, exporter: ReportExporter,
                 opener: FileOpener, clock: Clock, wallets: ManageWallets):
        self._session = session
        self._builder = builder
        self._exporter = exporter
        self._opener = opener
        self._clock = clock
        self._wallets = wallets

    def default_period(self) -> Period:
        data_range = self._session.ledger.date_range()
        start, end = data_range if data_range else (self._clock.today(),) * 2
        return Period(start, end)

    def build(self, period: Period) -> Report:
        return self._builder.build(self._session.ledger, period)

    def suggested_file_name(self, report: Report) -> str:
        p = report.period
        return f"rapport_{slug(self._wallets.active_name())}_{p.start:%Y%m%d}_{p.end:%Y%m%d}" \
               f"{self._exporter.file_extension}"

    def export(self, report: Report, destination: str) -> None:
        self._exporter.export(report, destination)

    def open_exported(self, destination: str) -> None:
        self._opener.open(destination)
