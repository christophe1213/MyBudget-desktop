"""Un portefeuille = un classeur Excel (openpyxl seul, sans pandas).

Feuilles : Transactions, Catégories (+ budget_jour), Solde par date, Détail catégories, Paramètres.
Seules « Transactions », « Catégories » et « Paramètres » sont relues ; les deux autres sont des synthèses.
"""
from __future__ import annotations

import os

from openpyxl import Workbook, load_workbook

from ....application.errors import StorageError
from ....application.ports.outbound import LedgerRepository
from ....domain.model.ledger import Ledger
from ....domain.services.balances import BalanceCalculator
from .codec import normalize_header, read_transactions
from .locations import FileLocationPolicy
from .styling import style_sheet

_DATE_FORMAT = "DD/MM/YYYY"


class ExcelLedgerRepository(LedgerRepository):
    def __init__(self, locations: FileLocationPolicy, balances: BalanceCalculator):
        self._locations = locations
        self._balances = balances

    def exists(self, location: str) -> bool:
        return os.path.exists(self._locations.resolve(location))

    # ---- lecture -----------------------------------------------------------------------------
    def load(self, location: str) -> Ledger:
        path = self._locations.resolve(location)
        if not os.path.exists(path):
            return Ledger()
        name = os.path.basename(path)
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except PermissionError as e:
            raise StorageError(f"Impossible de lire {name} : fermez-le dans Excel puis réessayez.",
                               locked=True) from e
        except Exception as e:  # noqa: BLE001
            raise StorageError(f"Impossible de lire {name} : {e}") from e
        try:
            if "Transactions" not in workbook.sheetnames:
                raise StorageError(f"{name} ne contient pas de feuille « Transactions ».")
            transactions = read_transactions(workbook["Transactions"])
            categories, budgets = self._read_categories(workbook)
            return Ledger(transactions, self._read_initial_balance(workbook), categories, budgets)
        except StorageError:
            raise
        except Exception as e:  # noqa: BLE001
            raise StorageError(f"{name} est invalide : {e}") from e
        finally:
            workbook.close()   # libère le fichier (important sous Windows)

    @staticmethod
    def _read_initial_balance(workbook) -> int:
        if "Paramètres" not in workbook.sheetnames:
            return 0
        for row in workbook["Paramètres"].iter_rows(min_row=2, values_only=True):
            if row and row[0] == "solde_initial" and row[1] is not None:
                return int(round(float(row[1])))
        return 0

    @staticmethod
    def _read_categories(workbook) -> tuple[list[str], dict[str, int]]:
        if "Catégories" not in workbook.sheetnames:
            return [], {}
        rows = workbook["Catégories"].iter_rows(values_only=True)
        header = next(rows, None) or ()
        columns = {normalize_header(h): i for i, h in enumerate(header)}
        if "categorie" not in columns:
            return [], {}
        names, budgets = [], {}
        for row in rows:
            name = str(row[columns["categorie"]] or "").strip() if len(row) > columns["categorie"] else ""
            if not name:
                continue
            names.append(name)
            i = columns.get("budget_jour")
            if i is not None and len(row) > i and row[i] not in (None, ""):
                budget = int(round(float(row[i])))
                if budget > 0:
                    budgets[name] = budget
        return names, budgets

    # ---- écriture ----------------------------------------------------------------------------
    def save(self, location: str, ledger: Ledger) -> None:
        path = self._locations.resolve(location)
        temp = path + ".tmp"
        try:
            self._build(ledger).save(temp)
            os.replace(temp, path)   # échoue si le classeur est ouvert dans Excel : rien n'est corrompu
        except PermissionError as e:
            self._discard(temp)
            raise StorageError(f"Impossible d'écrire {os.path.basename(path)} : fermez-le dans Excel "
                               "puis réessayez.", locked=True) from e
        except Exception as e:  # noqa: BLE001
            self._discard(temp)
            raise StorageError(f"Impossible d'écrire {os.path.basename(path)} : {e}") from e

    @staticmethod
    def _discard(temp: str) -> None:
        try:
            os.remove(temp)
        except OSError:
            pass

    def _build(self, ledger: Ledger) -> Workbook:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Transactions"
        sheet.append(["date", "categorie", "type", "libelle", "montant"])
        for t in sorted(ledger.transactions, key=lambda t: t.date):   # tri stable par date
            sheet.append([t.date, t.category, t.kind.value, t.label, t.amount])
            sheet.cell(sheet.max_row, 1).number_format = _DATE_FORMAT

        sheet = workbook.create_sheet("Catégories")
        sheet.append(["categorie", "budget_jour"])
        for c in ledger.categories:
            sheet.append([c, ledger.daily_budget(c)])

        sheet = workbook.create_sheet("Solde par date")
        sheet.append(["Date", "Dépôts", "Dépenses", "Solde"])
        for r in self._balances.by_date(ledger):
            sheet.append([r.date, r.deposits, r.expenses, r.balance])
            sheet.cell(sheet.max_row, 1).number_format = _DATE_FORMAT

        sheet = workbook.create_sheet("Détail catégories")
        sheet.append(["Date", "Catégorie", "Dépôts", "Dépenses", "Net (dépôts - dépenses)",
                      "Solde cumulé de la catégorie"])
        for r in self._balances.by_category(ledger):
            sheet.append([r.date, r.category, r.deposits, r.expenses, r.net, r.balance])
            sheet.cell(sheet.max_row, 1).number_format = _DATE_FORMAT

        sheet = workbook.create_sheet("Paramètres")
        sheet.append(["parametre", "valeur"])
        sheet.append(["solde_initial", ledger.initial_balance])

        for ws in workbook.worksheets:
            style_sheet(ws)
        return workbook
