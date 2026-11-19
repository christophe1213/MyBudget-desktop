from __future__ import annotations

import os

from openpyxl import Workbook

from ....application.errors import StorageError
from ....application.ports.outbound import ReportExporter
from ....domain.services.reports import Report
from .styling import style_sheet


class ExcelReportExporter(ReportExporter):
    """Écrit un rapport de période : feuilles Résumé, Par catégorie, Top dépenses."""

    file_extension = ".xlsx"

    def export(self, report: Report, destination: str) -> None:
        p = report.period
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Résumé"
        sheet.append(["Indicateur", "Valeur"])
        for row in [("Date de début", f"{p.start:%d/%m/%Y}"), ("Date de fin", f"{p.end:%d/%m/%Y}"),
                    ("Nombre de jours", p.days), ("Nombre de transactions", report.transaction_count),
                    ("Solde au début de la période", report.opening_balance),
                    ("Total des dépôts", report.total_deposits), ("Total des dépenses", report.total_expenses),
                    ("Net (dépôts - dépenses)", report.net),
                    ("Solde à la fin de la période", report.closing_balance),
                    ("Dépense moyenne par jour", report.average_daily_expense)]:
            sheet.append(list(row))

        sheet = workbook.create_sheet("Par catégorie")
        sheet.append(["Catégorie", "Dépôts", "Dépenses", "Net", "Part des dépenses (%)", "Nb transactions"])
        for c in report.categories:
            sheet.append([c.category, c.deposits, c.expenses, c.net, c.expense_share, c.count])

        sheet = workbook.create_sheet("Top dépenses")
        sheet.append(["Catégorie", "Libellé", "Dépenses"])
        for item in report.top_expenses:
            sheet.append([item.category, item.label, item.amount])

        for ws in workbook.worksheets:
            style_sheet(ws)
        try:
            workbook.save(destination)
        except PermissionError as e:
            raise StorageError(f"Impossible d'écrire {os.path.basename(destination)} : fermez-le dans Excel "
                               "puis réessayez.", locked=True) from e
        except Exception as e:  # noqa: BLE001
            raise StorageError(f"Export impossible : {e}") from e
