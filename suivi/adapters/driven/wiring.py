"""Lots d'adaptateurs pilotés prêts à brancher : c'est ICI (et dans main.py) qu'on choisit le stockage."""
from __future__ import annotations

import os

from ...application.ports.outbound import DrivenPorts
from ...domain.model.wallet import WalletRef
from ...domain.services.balances import BalanceCalculator
from .excel.importer import ExcelTransactionImporter
from .excel.locations import FileLocationPolicy
from .excel.repository import ExcelLedgerRepository
from .excel.report_exporter import ExcelReportExporter
from .sqlite.storage import SqliteDatabase, SqliteLedgerRepository, SqliteLocationPolicy, SqliteWalletRegistry
from .system import SystemClock, SystemFileOpener
from .text_registry import TextFileWalletRegistry

DEFAULT_WALLET_NAME = "Principal"


def excel_ports(data_dir: str) -> DrivenPorts:
    """Un classeur Excel par portefeuille ; la liste des portefeuilles dans portefeuilles.txt."""
    locations = FileLocationPolicy(data_dir)
    return DrivenPorts(
        ledgers=ExcelLedgerRepository(locations, BalanceCalculator()),
        locations=locations,
        registry=TextFileWalletRegistry(data_dir, "portefeuilles.txt",
                                        WalletRef(DEFAULT_WALLET_NAME, "transactions.xlsx")),
        importer=ExcelTransactionImporter(), exporter=ExcelReportExporter(),
        opener=SystemFileOpener(), clock=SystemClock())


def sqlite_ports(data_dir: str) -> DrivenPorts:
    """Tous les portefeuilles dans une seule base SQLite (suivi.db). L'import/export restent en Excel."""
    database = SqliteDatabase(os.path.join(data_dir, "suivi.db"))
    return DrivenPorts(
        ledgers=SqliteLedgerRepository(database), locations=SqliteLocationPolicy(),
        registry=SqliteWalletRegistry(database, WalletRef(DEFAULT_WALLET_NAME, "principal")),
        importer=ExcelTransactionImporter(), exporter=ExcelReportExporter(),
        opener=SystemFileOpener(), clock=SystemClock())
