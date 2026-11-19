"""Ledger (livre de comptes) : le contenu d'un portefeuille et ses règles métier.

Python pur : aucune dépendance à un format de stockage ni à une interface.
Invariants : toute transaction appartient à une catégorie connue ; les noms de catégories sont uniques
(sans tenir compte de la casse) ; un budget par jour n'existe que pour une catégorie connue.
"""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
from typing import Iterable, Optional

from .errors import DomainError
from .transaction import Kind, Transaction


def sort_categories(names: Iterable[str]) -> list[str]:
    return sorted(set(names), key=str.casefold)


class Ledger:
    def __init__(self, transactions: Iterable[Transaction] = (), initial_balance: int = 0,
                 categories: Iterable[str] = (), budgets: Optional[dict] = None):
        self._transactions: list[Transaction] = list(transactions)
        self._initial_balance = int(initial_balance)
        used = {t.category for t in self._transactions if t.category}
        self._categories: list[str] = sort_categories({c for c in categories if c} | used)
        self._budgets: dict[str, int] = {c: int(b) for c, b in (budgets or {}).items()
                                         if c in self._categories and int(b) > 0}

    def copy(self) -> "Ledger":
        clone = copy.copy(self)
        clone._transactions = list(self._transactions)
        clone._categories = list(self._categories)
        clone._budgets = dict(self._budgets)
        return clone

    # ---- lecture ---------------------------------------------------------------------------
    @property
    def transactions(self) -> tuple[Transaction, ...]:
        return tuple(self._transactions)

    @property
    def initial_balance(self) -> int:
        return self._initial_balance

    @property
    def categories(self) -> list[str]:
        return list(self._categories)

    @property
    def budgets(self) -> dict[str, int]:
        return dict(self._budgets)

    def daily_budget(self, category: str) -> int:
        return self._budgets.get(category, 0)

    def transactions_on(self, day: dt.date) -> list[tuple[int, Transaction]]:
        """(identifiant, transaction) ; l'identifiant sert à désigner la transaction à supprimer."""
        return [(i, t) for i, t in enumerate(self._transactions) if t.date == day]

    def date_range(self) -> Optional[tuple[dt.date, dt.date]]:
        if not self._transactions:
            return None
        dates = [t.date for t in self._transactions]
        return min(dates), max(dates)

    # ---- catégories ------------------------------------------------------------------------
    def has_category(self, name: str, ignore: Optional[str] = None) -> bool:
        return any(c.casefold() == name.casefold() for c in self._categories if c != ignore)

    def category_usage(self, name: str) -> int:
        return sum(1 for t in self._transactions if t.category == name)

    def add_category(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise DomainError("Le nom ne peut pas être vide.")
        if self.has_category(name):
            raise DomainError(f"La catégorie « {name} » existe déjà.")
        self._categories = sort_categories(self._categories + [name])

    def rename_category(self, old: str, new: str) -> None:
        new = new.strip()
        if old not in self._categories:
            raise DomainError("Catégorie inconnue.")
        if not new:
            raise DomainError("Le nom ne peut pas être vide.")
        if self.has_category(new, ignore=old):
            raise DomainError(f"La catégorie « {new} » existe déjà.")
        self._transactions = [dataclasses.replace(t, category=new) if t.category == old else t
                              for t in self._transactions]
        self._categories = sort_categories(new if c == old else c for c in self._categories)
        if old in self._budgets:
            self._budgets[new] = self._budgets.pop(old)

    def remove_category(self, name: str) -> None:
        usage = self.category_usage(name)
        if usage:
            raise DomainError(f"La catégorie « {name} » est utilisée par {usage} transaction(s).\n"
                              "Renommez-la, ou supprimez d'abord ces transactions.")
        self._categories = [c for c in self._categories if c != name]
        self._budgets.pop(name, None)

    def set_daily_budget(self, category: str, amount: int) -> None:
        """Budget par jour d'une catégorie ; 0 le supprime."""
        if category not in self._categories:
            raise DomainError("Catégorie inconnue.")
        if amount < 0:
            raise DomainError("Le budget ne peut pas être négatif.")
        if amount > 0:
            self._budgets[category] = int(amount)
        else:
            self._budgets.pop(category, None)

    # ---- transactions ----------------------------------------------------------------------
    def add_transaction(self, date: dt.date, category: str, kind: Kind, label: str, amount: int) -> None:
        if category not in self._categories:
            raise DomainError("Choisissez une catégorie dans la liste.")
        if amount <= 0:
            raise DomainError("Montant invalide (entier positif attendu).")
        label = label.strip() or (kind.value if kind is Kind.DEPOSIT else "")
        self._transactions.append(Transaction(date, category, kind, label, int(amount)))

    def add_deposits(self, lines: Iterable[tuple[str, int]], date: dt.date, label: str) -> int:
        """Un dépôt par (catégorie, montant > 0) ; retourne le nombre de dépôts créés."""
        created = [Transaction(date, c, Kind.DEPOSIT, label, int(m))
                   for c, m in lines if m > 0 and c in self._categories]
        self._transactions.extend(created)
        return len(created)

    def remove_transactions(self, ids: Iterable[int]) -> None:
        gone = set(ids)
        self._transactions = [t for i, t in enumerate(self._transactions) if i not in gone]

    def categories_with_deposit(self, categories: Iterable[str], label: str) -> list[str]:
        """Parmi `categories`, celles qui ont déjà un dépôt portant ce libellé."""
        wanted = set(categories)
        return sorted({t.category for t in self._transactions
                       if t.kind is Kind.DEPOSIT and t.label == label and t.category in wanted})

    def new_categories_in(self, transactions: Iterable[Transaction]) -> list[str]:
        found: list[str] = []
        for t in transactions:
            if t.category and not self.has_category(t.category) and t.category not in found:
                found.append(t.category)
        return found

    def merge(self, transactions: Iterable[Transaction]) -> None:
        """Ajoute des transactions importées (et crée leurs catégories manquantes)."""
        incoming = list(transactions)
        self._categories = sort_categories(self._categories + self.new_categories_in(incoming))
        self._transactions.extend(incoming)

    # ---- paramètres ------------------------------------------------------------------------
    def set_initial_balance(self, amount: int) -> None:
        self._initial_balance = int(amount)
