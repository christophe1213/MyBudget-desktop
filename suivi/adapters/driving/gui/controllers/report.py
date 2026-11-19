from __future__ import annotations

from typing import Optional

from .....application.ports.inbound import BuildReports, EventSource
from .....domain.model.period import Period
from .....domain.services.reports import Report
from ..contract.dto import Row
from ..contract.interfaces import Dialogs, ReportListener, ReportView
from ..formatting import format_ar, format_date
from ..parsing import parse_date
from .base import Controller

_PLACEHOLDER = "Choisissez deux dates puis cliquez sur « Générer le rapport »."


class ReportController(Controller, ReportListener):
    """Onglet « Rapport » : somme des dépôts et dépenses par catégorie entre deux dates."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: ReportView, reports: BuildReports,
                 export_dir: str):
        super().__init__(events, dialogs)
        self._view = view
        self._reports = reports
        self._export_dir = export_dir
        self._report: Optional[Report] = None
        self._period_ready = False
        view.set_listener(self)

    def reset(self) -> None:
        self._period_ready = False
        self._report = None
        self._view.reset(_PLACEHOLDER)

    def on_imported(self) -> None:
        self._period_ready = False  # la période par défaut couvre les nouvelles données
        self.refresh()

    def refresh(self) -> None:
        if self._period_ready:
            return
        period = self._reports.default_period()
        self._view.set_period(format_date(period.start), format_date(period.end))
        self._period_ready = True

    def on_generate(self) -> None:
        with self.guard("Rapport"):
            start, end = (parse_date(t) for t in self._view.get_period())
            report = self._reports.build(Period(start, end))
            self._report = report
            rows = [Row(str(i), (c.category, format_ar(c.deposits), format_ar(c.expenses), format_ar(c.net),
                                 f"{c.expense_share:.1f} %", c.count))
                    for i, c in enumerate(report.categories)]
            rows.append(Row("total", ("TOTAL", format_ar(report.total_deposits),
                                      format_ar(report.total_expenses), format_ar(report.net),
                                      "100 %" if report.total_expenses else "", report.transaction_count),
                            emphasis=True))
            self._view.show_report(
                f"Période : {format_date(report.period.start)} au {format_date(report.period.end)} "
                f"({report.period.days} jours)\n"
                f"Solde au début : {format_ar(report.opening_balance)}      "
                f"Solde à la fin : {format_ar(report.closing_balance)}\n"
                f"Total dépôts : {format_ar(report.total_deposits)}      "
                f"Total dépenses : {format_ar(report.total_expenses)}      "
                f"Dépense moyenne par jour : {format_ar(report.average_daily_expense)}", rows)

    def on_export(self) -> None:
        if self._report is None:
            self.on_generate()
            if self._report is None:
                return
        path = self._dialogs.ask_save_file("Exporter le rapport", self._export_dir,
                                           self._reports.suggested_file_name(self._report))
        if not path:
            return
        with self.guard("Export impossible"):
            self._reports.export(self._report, path)
            if self._dialogs.confirm("Rapport exporté", "Rapport enregistré. L'ouvrir maintenant ?"):
                self._reports.open_exported(path)
