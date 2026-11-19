"""Faux adaptateurs EN MÉMOIRE : l'application tourne sans fichier, sans Excel, sans base, sans fenêtre."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

from suivi.adapters.driving.gui.contract import interfaces as v
from suivi.application.errors import StorageError
from suivi.application.naming import slug
from suivi.application.ports.outbound import (Clock, DrivenPorts, FileOpener, LedgerRepository, LocationPolicy,
                                              ReportExporter, TransactionImporter, WalletRegistry)
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.wallet import WalletCatalog, WalletRef


class InMemoryLedgers(LedgerRepository):
    def __init__(self):
        self.stored: dict[str, Ledger] = {}
        self.fail_on_save: StorageError | None = None

    def exists(self, location):
        return location in self.stored

    def load(self, location):
        return self.stored[location].copy() if location in self.stored else Ledger()

    def save(self, location, ledger):
        if self.fail_on_save:
            raise self.fail_on_save
        self.stored[location] = ledger.copy()


class InMemoryLocations(LocationPolicy):
    link_patterns = ("*.mem",)

    def suggest_location(self, wallet_name, taken):
        taken, base, n, candidate = set(taken), slug(wallet_name), 2, slug(wallet_name)
        while candidate in taken:
            candidate, n = f"{base}_{n}", n + 1
        return candidate

    def location_from_path(self, path):
        return path.rsplit("/", 1)[-1]

    def canonical(self, location):
        return location.casefold()

    def storage_path(self, location):
        return None


class InMemoryRegistry(WalletRegistry):
    def __init__(self):
        self.catalog = WalletCatalog((WalletRef("Principal", "principal"),), "Principal")

    def load(self):
        return self.catalog

    def save(self, catalog):
        self.catalog = catalog


class FixedClock(Clock):
    def __init__(self, today=dt.date(2026, 10, 1)):
        self._now = dt.datetime.combine(today, dt.time(9, 0))

    def today(self):
        return self._now.date()

    def now(self):
        return self._now

    def advance(self, **delta):
        self._now += dt.timedelta(**delta)


class RecordingOpener(FileOpener):
    def __init__(self):
        self.opened = []

    def open(self, path):
        self.opened.append(path)


class FakeImporter(TransactionImporter):
    patterns = ("*.mem",)

    def __init__(self, transactions=()):
        self.transactions = list(transactions)

    def read(self, source):
        return list(self.transactions)


class FakeExporter(ReportExporter):
    file_extension = ".txt"

    def __init__(self):
        self.exported = []

    def export(self, report, destination):
        self.exported.append((report, destination))


def make_ports() -> DrivenPorts:
    return DrivenPorts(ledgers=InMemoryLedgers(), locations=InMemoryLocations(), registry=InMemoryRegistry(),
                       importer=FakeImporter(), exporter=FakeExporter(), opener=RecordingOpener(),
                       clock=FixedClock())


def make_ui() -> SimpleNamespace:
    """Interface « simulée » : chaque vue est un mock qui respecte le contrat (spec)."""
    ui = SimpleNamespace(
        dialogs=MagicMock(spec=v.Dialogs), navigator=MagicMock(spec=v.Navigator),
        header=MagicMock(spec=v.HeaderView), dashboard=MagicMock(spec=v.DashboardView),
        transactions=MagicMock(spec=v.TransactionsView),
        balances=MagicMock(spec=v.BalanceView), category_details=MagicMock(spec=v.CategoryDetailView),
        categories=MagicMock(spec=v.CategoryManagerView), report=MagicMock(spec=v.ReportView),
        budget=MagicMock(spec=v.BudgetView), analysis=MagicMock(spec=v.AnalysisView),
        wallets=MagicMock(spec=v.WalletsView), run=MagicMock())
    ui.dialogs.confirm.return_value = True
    ui.category_details.get_filters.return_value = ("Toutes", "Toutes")
    ui.dashboard.get_period.return_value = ("", "")
    ui.transactions.get_category.return_value = ""
    ui.transactions.get_date_text.return_value = "01/09/2026"
    ui.analysis.get_category.return_value = ""
    ui.analysis.get_budget_text.return_value = ""
    return ui


# ---- authentification : adaptateurs en mémoire -----------------------------------------------------------
import dataclasses  # noqa: E402

from suivi.application.dto import LocalSession  # noqa: E402
from suivi.application.ports.outbound import (AccountRepository, AuthPorts, LocalSessionStore,  # noqa: E402
                                              PasswordHasher, RememberTokens)
from suivi.domain.model.errors import DomainError  # noqa: E402


class FastHasher(PasswordHasher):
    """Pas de vrai hachage (rapide pour les tests) : l'application ne dépend que du contrat."""

    def hash(self, secret):
        return "h:" + secret[::-1]

    def verify(self, secret, hashed):
        return hashed == "h:" + secret[::-1]


class InMemoryAccounts(AccountRepository):
    def __init__(self):
        self.rows = {}

    def count(self):
        return len(self.rows)

    def add(self, account):
        if any(a.email == account.email for a in self.rows.values()):
            raise DomainError("Un compte existe déjà avec cette adresse e-mail.")
        saved = dataclasses.replace(account, id=len(self.rows) + 1)
        self.rows[saved.id] = saved
        return saved

    def by_email(self, email):
        return next((a for a in self.rows.values() if a.email == email), None)

    def by_id(self, account_id):
        return self.rows.get(account_id)

    def update(self, account):
        self.rows[account.id] = account


class InMemoryTokens(RememberTokens):
    def __init__(self):
        self.tokens = {}      # jeton -> (compte, expiration)

    def issue(self, account_id, expires_at):
        token = f"tok{len(self.tokens)}"
        self.tokens[token] = (account_id, expires_at)
        return token

    def resolve(self, token, now):
        found = self.tokens.get(token)
        return found[0] if found and found[1] > now else None

    def revoke(self, token):
        self.tokens.pop(token, None)

    def revoke_all(self, account_id):
        self.tokens = {k: v for k, v in self.tokens.items() if v[0] != account_id}


class InMemoryLocalSession(LocalSessionStore):
    def __init__(self):
        self.session = LocalSession()

    def load(self):
        return self.session

    def save(self, session):
        self.session = session


def make_auth_ports() -> AuthPorts:
    return AuthPorts(InMemoryAccounts(), FastHasher(), InMemoryTokens(), InMemoryLocalSession())
