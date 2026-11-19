"""PORTS SORTANTS : ce dont l'application a besoin du monde extérieur.

L'application les définit ; les adaptateurs « pilotés » (Excel, SQLite, système...) les implémentent.
Changer de stockage = écrire de nouvelles classes pour ces interfaces, sans toucher au reste.
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Optional

from ...domain.model.account import Account
from ...domain.model.ledger import Ledger
from ...domain.model.transaction import Transaction
from ...domain.model.wallet import WalletCatalog
from ...domain.services.reports import Report
from ..dto import LocalSession


class LedgerRepository(ABC):
    """Lire / écrire le livre de comptes d'un portefeuille. `location` est opaque pour l'application."""

    @abstractmethod
    def exists(self, location: str) -> bool: ...

    @abstractmethod
    def load(self, location: str) -> Ledger:
        """Livre vide si l'emplacement n'existe pas. Lève StorageError si la lecture échoue."""

    @abstractmethod
    def save(self, location: str, ledger: Ledger) -> None:
        """Lève StorageError si l'écriture échoue (avec locked=True si la ressource est occupée)."""


class LocationPolicy(ABC):
    """Règles propres à un type de stockage : nommage, normalisation, accès « fichier »."""

    link_patterns: tuple = ()   # types de fichiers que l'utilisateur peut « associer » (ex. ('*.xlsx',))

    @abstractmethod
    def suggest_location(self, wallet_name: str, taken: Iterable[str]) -> str:
        """Nouvel emplacement libre pour un nouveau portefeuille."""

    @abstractmethod
    def location_from_path(self, path: str) -> str:
        """Emplacement correspondant à un fichier choisi par l'utilisateur (DomainError si impossible)."""

    @abstractmethod
    def canonical(self, location: str) -> str:
        """Forme normalisée, pour détecter deux emplacements identiques."""

    @abstractmethod
    def storage_path(self, location: str) -> Optional[str]:
        """Chemin d'un fichier ouvrable par l'utilisateur, ou None si le stockage n'en a pas."""


class WalletRegistry(ABC):
    """Mémorise la liste des portefeuilles et le portefeuille actif."""

    @abstractmethod
    def load(self) -> WalletCatalog: ...

    @abstractmethod
    def save(self, catalog: WalletCatalog) -> None: ...


class TransactionImporter(ABC):
    patterns: tuple = ()   # types de fichiers lisibles

    @abstractmethod
    def read(self, source: str) -> list[Transaction]: ...


class ReportExporter(ABC):
    file_extension: str = ""   # ex. '.xlsx'

    @abstractmethod
    def export(self, report: Report, destination: str) -> None: ...


class FileOpener(ABC):
    @abstractmethod
    def open(self, path: str) -> None: ...


class Clock(ABC):
    @abstractmethod
    def today(self) -> dt.date: ...

    @abstractmethod
    def now(self) -> dt.datetime: ...


@dataclass(frozen=True)
class DrivenPorts:
    """Tout ce que `bootstrap` attend des adaptateurs pilotés (un lot cohérent)."""
    ledgers: LedgerRepository
    locations: LocationPolicy
    registry: WalletRegistry
    importer: TransactionImporter
    exporter: ReportExporter
    opener: FileOpener
    clock: Clock


# ---- authentification ------------------------------------------------------------------------------
class AccountRepository(ABC):
    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def add(self, account: Account) -> Account:
        """Enregistre un nouveau compte et le retourne avec son identifiant (DomainError si l'e-mail existe)."""

    @abstractmethod
    def by_email(self, email: str) -> Optional[Account]: ...

    @abstractmethod
    def by_id(self, account_id: int) -> Optional[Account]: ...

    @abstractmethod
    def update(self, account: Account) -> None: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, secret: str) -> str: ...

    @abstractmethod
    def verify(self, secret: str, hashed: str) -> bool: ...


class RememberTokens(ABC):
    """Jetons « Rester connecté » : seule leur empreinte est conservée côté stockage."""

    @abstractmethod
    def issue(self, account_id: int, expires_at: dt.datetime) -> str:
        """Crée un jeton secret (retourné une seule fois) valable jusqu'à `expires_at`."""

    @abstractmethod
    def resolve(self, token: str, now: dt.datetime) -> Optional[int]:
        """Identifiant du compte si le jeton existe et n'a pas expiré, sinon None."""

    @abstractmethod
    def revoke(self, token: str) -> None: ...

    @abstractmethod
    def revoke_all(self, account_id: int) -> None: ...


class LocalSessionStore(ABC):
    @abstractmethod
    def load(self) -> LocalSession: ...

    @abstractmethod
    def save(self, session: LocalSession) -> None: ...


@dataclass(frozen=True)
class AuthPorts:
    """Adaptateurs pilotés de l'authentification (indépendants de ceux des données financières)."""
    accounts: AccountRepository
    hasher: PasswordHasher
    tokens: RememberTokens
    local: LocalSessionStore
