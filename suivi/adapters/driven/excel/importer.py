from __future__ import annotations

from openpyxl import load_workbook

from ....application.errors import StorageError
from ....application.ports.outbound import TransactionImporter
from ....domain.model.transaction import Transaction
from .codec import read_transactions


class ExcelTransactionImporter(TransactionImporter):
    """Lit les transactions d'un classeur Excel (feuille « Transactions », sinon la première)."""

    patterns = ("*.xlsx",)

    def read(self, source: str) -> list[Transaction]:
        try:
            workbook = load_workbook(source, read_only=True, data_only=True)
        except Exception as e:  # noqa: BLE001
            raise StorageError(f"Impossible de lire {source} : {e}") from e
        try:
            sheet = workbook["Transactions"] if "Transactions" in workbook.sheetnames else workbook.worksheets[0]
            return read_transactions(sheet)
        except Exception as e:  # noqa: BLE001
            raise StorageError(f"Fichier invalide : {e}") from e
        finally:
            workbook.close()
