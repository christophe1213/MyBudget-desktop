"""PORTS ENTRANTS : ce que l'application offre aux adaptateurs « pilotants » (interface graphique...).

Un adaptateur d'interface (tkinter, customtkinter, ligne de commande, API web...) ne parle à
l'application qu'à travers ces interfaces. Les cas d'usage (use_cases/) les implémentent.
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from typing import Callable, Iterable, Optional

from ...domain.model.period import Period
from ...domain.model.transaction import Kind, Transaction
from ...domain.model.wallet import WalletRef
from ...domain.services.balances import CategoryBalance, DayBalance
from ...domain.services.budget import BudgetLine
from ...domain.services.dashboard import BudgetShares, FlowSeries
from ...domain.services.reports import Report
from ...domain.services.spending import SpendingAnalysis, SpendingStats
from ..dto import CategoryInfo, ImportPreview, Registration, SyncExport, SyncReport, UserInfo, WalletSummary


class EventSource(ABC):
    @abstractmethod
    def subscribe(self, callback: Callable) -> None:
        """`callback(event)` est appelé après chaque changement (voir application.events.Event)."""


class ManageTransactions(ABC):
    @abstractmethod
    def categories(self) -> list[str]: ...

    @abstractmethod
    def transactions_on(self, day: dt.date) -> list[tuple[int, Transaction]]: ...

    @abstractmethod
    def balance_at(self, day: dt.date) -> int: ...

    @abstractmethod
    def add(self, day: dt.date, category: str, kind: Kind, label: str, amount: int) -> None: ...

    @abstractmethod
    def delete(self, ids: list[int]) -> None: ...


class ManageLedger(ABC):
    @abstractmethod
    def initial_balance(self) -> int: ...

    @abstractmethod
    def set_initial_balance(self, amount: int) -> None: ...

    @abstractmethod
    def import_patterns(self) -> tuple: ...

    @abstractmethod
    def preview_import(self, source: str) -> ImportPreview: ...

    @abstractmethod
    def import_transactions(self, preview: ImportPreview) -> None: ...

    @abstractmethod
    def open_storage_file(self) -> None: ...


class ManageCategories(ABC):
    @abstractmethod
    def list_categories(self) -> list[CategoryInfo]: ...

    @abstractmethod
    def add(self, name: str) -> None: ...

    @abstractmethod
    def rename(self, old: str, new: str) -> None: ...

    @abstractmethod
    def remove(self, name: str) -> None: ...

    @abstractmethod
    def daily_budget(self, category: str) -> int: ...

    @abstractmethod
    def set_daily_budget(self, category: str, amount: int) -> None: ...

    @abstractmethod
    def has_daily_budgets(self) -> bool: ...


class QueryBalances(ABC):
    @abstractmethod
    def categories(self) -> list[str]: ...

    @abstractmethod
    def transaction_dates(self) -> list[dt.date]: ...

    @abstractmethod
    def balance_by_date(self) -> list[DayBalance]: ...

    @abstractmethod
    def category_balances(self) -> list[CategoryBalance]: ...


class BuildReports(ABC):
    @abstractmethod
    def default_period(self) -> Period: ...

    @abstractmethod
    def build(self, period: Period) -> Report: ...

    @abstractmethod
    def suggested_file_name(self, report: Report) -> str: ...

    @abstractmethod
    def export(self, report: Report, destination: str) -> None: ...

    @abstractmethod
    def open_exported(self, destination: str) -> None: ...


class PlanBudgets(ABC):
    @abstractmethod
    def default_period(self) -> Period: ...

    @abstractmethod
    def propose(self, period: Period) -> list[BudgetLine]: ...

    @abstractmethod
    def deposit_label(self, period: Period) -> str: ...

    @abstractmethod
    def categories_with_deposit(self, categories: Iterable[str], label: str) -> list[str]: ...

    @abstractmethod
    def create_deposits(self, period: Period, lines: list[tuple[str, int]]) -> int: ...


class AnalyzeSpending(ABC):
    @abstractmethod
    def categories(self) -> list[str]: ...

    @abstractmethod
    def default_period(self) -> Period: ...

    @abstractmethod
    def analyze(self, category: str, period: Period) -> SpendingAnalysis: ...

    @abstractmethod
    def diagnose(self, stats: SpendingStats) -> str: ...

    @abstractmethod
    def daily_budget(self, category: str) -> int: ...


class ManageWallets(ABC):
    @abstractmethod
    def start(self) -> None:
        """Ouvre le portefeuille actif au démarrage."""

    @abstractmethod
    def names(self) -> list[str]: ...

    @abstractmethod
    def active_name(self) -> str: ...

    @abstractmethod
    def summaries(self) -> list[WalletSummary]: ...

    @abstractmethod
    def link_patterns(self) -> tuple: ...

    @abstractmethod
    def open(self, name: str) -> None: ...

    @abstractmethod
    def create(self, name: str) -> WalletRef: ...

    @abstractmethod
    def prepare_link(self, path: str) -> str:
        """Vérifie qu'un fichier existant peut devenir un portefeuille ; retourne son emplacement."""

    @abstractmethod
    def link(self, name: str, location: str) -> None: ...

    @abstractmethod
    def rename(self, old: str, new: str) -> None: ...

    @abstractmethod
    def remove(self, name: str) -> None: ...


class Authenticate(ABC):
    @abstractmethod
    def has_accounts(self) -> bool: ...

    @abstractmethod
    def last_known_name(self) -> Optional[str]:
        """Nom de la dernière personne connectée sur ce poste (pour la saluer)."""

    @abstractmethod
    def last_known_email(self) -> Optional[str]: ...

    @abstractmethod
    def resume(self) -> Optional[UserInfo]:
        """Reconnecte automatiquement si « Rester connecté » était coché et que le jeton est valide."""

    @abstractmethod
    def login(self, email: str, password: str, remember: bool) -> UserInfo: ...

    @abstractmethod
    def register(self, name: str, email: str, password: str, confirmation: str) -> Registration: ...

    @abstractmethod
    def reset_password(self, email: str, recovery_key: str, new_password: str) -> str:
        """Change le mot de passe ; retourne la NOUVELLE clé de récupération (l'ancienne est invalidée)."""

    @abstractmethod
    def logout(self) -> None: ...

    @abstractmethod
    def current_user(self) -> Optional[UserInfo]: ...


class ViewDashboard(ABC):
    @abstractmethod
    def budget_shares(self) -> BudgetShares:
        """Solde restant de chaque budget (catégorie) : positifs pour le camembert, déficits à part."""

    @abstractmethod
    def data_period(self) -> Optional[Period]:
        """Première et dernière date des transactions, ou None s'il n'y en a pas."""

    @abstractmethod
    def default_period(self) -> Period: ...

    @abstractmethod
    def flows(self, period: Period) -> FlowSeries:
        """Entrées (dépôts) et sorties (dépenses) de chaque jour de la période."""


class SynchronizeData(ABC):
    """Échanger les données avec un autre appareil et tenir le journal de ces échanges."""

    @abstractmethod
    def export_payload(self, start: Optional[dt.date]) -> SyncExport:
        """Données de tous les portefeuilles lisibles, à partir de `start` (None = tout l'historique)."""

    @abstractmethod
    def receive(self, payload) -> SyncReport:
        """Valide des données reçues (DomainError si invalides) puis fusionne leurs nouvelles transactions
        dans les portefeuilles du même nom. Rien n'est supprimé ni écrasé."""

    @abstractmethod
    def record(self, kind: str, message: str) -> str:
        """Ajoute une ligne au journal de synchronisation ; retourne la ligne écrite (jamais d'exception)."""

    @abstractmethod
    def recent_entries(self, count: int = 50) -> list[str]: ...

    @abstractmethod
    def journal_location(self) -> str: ...
