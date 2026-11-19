"""Stockage SQLite (bibliothèque standard uniquement) : même contrat que l'Excel, autre technologie.

Prouve que le cœur de l'application ne dépend pas du format de stockage : pour passer de l'Excel à
SQLite, on remplace les adaptateurs dans `wiring.py`, rien d'autre.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import closing
from typing import Iterable, Optional

from ....application.errors import StorageError
from ....application.naming import slug
from ....application.ports.outbound import LedgerRepository, LocationPolicy, WalletRegistry
from ....domain.model.errors import DomainError
from ....domain.model.ledger import Ledger
from ....domain.model.transaction import Kind, Transaction
from ....domain.model.wallet import WalletCatalog, WalletRef

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets(position INTEGER PRIMARY KEY AUTOINCREMENT,
                                   name TEXT NOT NULL UNIQUE, location TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledgers(location TEXT PRIMARY KEY, initial_balance INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS categories(location TEXT NOT NULL, name TEXT NOT NULL,
                                      daily_budget INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(location, name));
CREATE TABLE IF NOT EXISTS transactions(location TEXT NOT NULL, position INTEGER NOT NULL, date TEXT NOT NULL,
                                        category TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL,
                                        amount INTEGER NOT NULL, PRIMARY KEY(location, position));
"""


class SqliteDatabase:
    def __init__(self, path: str):
        self._path = path

    def connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self._path, timeout=5)
            connection.executescript(_SCHEMA)
            return connection
        except sqlite3.Error as e:
            raise self.error(e) from e

    @staticmethod
    def error(e: sqlite3.Error) -> StorageError:
        return StorageError(f"Base de données inaccessible : {e}", locked="locked" in str(e).lower())


class SqliteLedgerRepository(LedgerRepository):
    def __init__(self, database: SqliteDatabase):
        self._db = database

    def exists(self, location: str) -> bool:
        with closing(self._db.connect()) as con:
            return con.execute("SELECT 1 FROM ledgers WHERE location=?", (location,)).fetchone() is not None

    def load(self, location: str) -> Ledger:
        try:
            with closing(self._db.connect()) as con:
                head = con.execute("SELECT initial_balance FROM ledgers WHERE location=?", (location,)).fetchone()
                if head is None:
                    return Ledger()
                cats = con.execute("SELECT name, daily_budget FROM categories WHERE location=?", (location,)).fetchall()
                rows = con.execute("SELECT date, category, kind, label, amount FROM transactions "
                                   "WHERE location=? ORDER BY position", (location,)).fetchall()
            transactions = [Transaction(dt.date.fromisoformat(d), c, Kind(k), lbl, a) for d, c, k, lbl, a in rows]
            return Ledger(transactions, head[0], [n for n, _b in cats], {n: b for n, b in cats if b > 0})
        except sqlite3.Error as e:
            raise self._db.error(e) from e
        except ValueError as e:
            raise StorageError(f"Données invalides en base : {e}") from e

    def save(self, location: str, ledger: Ledger) -> None:
        try:
            with closing(self._db.connect()) as con, con:   # une seule transaction : tout ou rien
                con.execute("INSERT INTO ledgers(location, initial_balance) VALUES(?, ?) "
                            "ON CONFLICT(location) DO UPDATE SET initial_balance=excluded.initial_balance",
                            (location, ledger.initial_balance))
                con.execute("DELETE FROM categories WHERE location=?", (location,))
                con.execute("DELETE FROM transactions WHERE location=?", (location,))
                con.executemany("INSERT INTO categories VALUES(?, ?, ?)",
                                [(location, c, ledger.daily_budget(c)) for c in ledger.categories])
                con.executemany("INSERT INTO transactions VALUES(?, ?, ?, ?, ?, ?, ?)",
                                [(location, i, t.date.isoformat(), t.category, t.kind.value, t.label, t.amount)
                                 for i, t in enumerate(ledger.transactions)])
        except sqlite3.Error as e:
            raise self._db.error(e) from e


class SqliteLocationPolicy(LocationPolicy):
    """Ici l'emplacement d'un portefeuille est une simple clé texte dans la base."""

    link_patterns = ()   # pas de « fichier à associer » avec ce stockage

    def suggest_location(self, wallet_name: str, taken: Iterable[str]) -> str:
        used = set(taken)
        base, candidate, n = slug(wallet_name), slug(wallet_name), 2
        while candidate in used:
            candidate, n = f"{base}_{n}", n + 1
        return candidate

    def location_from_path(self, path: str) -> str:
        raise DomainError("L'association d'un fichier n'est pas disponible avec la base SQLite.")

    def canonical(self, location: str) -> str:
        return location

    def storage_path(self, location: str) -> Optional[str]:
        return None


class SqliteWalletRegistry(WalletRegistry):
    def __init__(self, database: SqliteDatabase, default: WalletRef):
        self._db = database
        self._default = default

    def load(self) -> WalletCatalog:
        try:
            with closing(self._db.connect()) as con:
                rows = con.execute("SELECT name, location FROM wallets ORDER BY position").fetchall()
                active = con.execute("SELECT value FROM meta WHERE key='active'").fetchone()
        except sqlite3.Error as e:
            raise self._db.error(e) from e
        return WalletCatalog(tuple(WalletRef(n, loc) for n, loc in rows) or (self._default,),
                             active[0] if active else "")

    def save(self, catalog: WalletCatalog) -> None:
        try:
            with closing(self._db.connect()) as con, con:
                con.execute("DELETE FROM wallets")
                con.executemany("INSERT INTO wallets(name, location) VALUES(?, ?)",
                                [(w.name, w.location) for w in catalog.wallets])
                con.execute("INSERT INTO meta(key, value) VALUES('active', ?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (catalog.active,))
        except sqlite3.Error as e:
            raise self._db.error(e) from e
