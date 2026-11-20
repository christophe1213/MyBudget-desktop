"""Réception : JSON « repere » (version 1) -> livres de comptes du domaine.

Python pur, comme `repere_format.py` dont c'est l'inverse. Tout ce qui arrive de l'extérieur est VALIDÉ ici,
avant d'atteindre le domaine : en cas de donnée invalide on lève `DomainError` (message destiné à
l'utilisateur) et rien n'est modifié.

Deux limites viennent du domaine, qui ne gère que des montants entiers (Ariary) et un seul solde initial
par portefeuille :
  - un montant non entier est refusé (jamais arrondi en silence) ;
  - le solde de départ d'une catégorie (`initialBalance`) n'est pas repris : il est signalé dans `warnings`.
Les identifiants reçus ne sont pas conservés (le domaine n'en a pas) ; `new_transactions` évite les doublons
en comparant le contenu des transactions.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter
from dataclasses import dataclass
from itertools import chain
from typing import Union

from ..domain.model.errors import DomainError
from ..domain.model.ledger import Ledger
from ..domain.model.transaction import Kind, Transaction
from .repere_format import FORMAT_NAME, FORMAT_VERSION

_KINDS = {"deposit": Kind.DEPOSIT, "expense": Kind.EXPENSE}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ReceivedWallet:
    id: str                          # identifiant de l'appareil émetteur (sert à retrouver le portefeuille)
    name: str
    ledger: Ledger
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Reception:
    wallets: tuple[ReceivedWallet, ...]
    active: str                      # nom du portefeuille actif côté émetteur

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(chain.from_iterable(w.warnings for w in self.wallets))


def repere_to_ledgers(data: Union[dict, str, bytes]) -> Reception:
    """Valide des données « repere » (dictionnaire, ou texte/octets JSON) et les convertit en livres de comptes."""
    payload = _as_object(data)
    if payload.get("format") != FORMAT_NAME:
        raise DomainError("Ces données ne sont pas au format « repere ».")
    if payload.get("version") != FORMAT_VERSION:
        raise DomainError(f"Version {payload.get('version')!r} non prise en charge (attendu : {FORMAT_VERSION}).")
    raw_wallets = payload.get("wallets")
    if not isinstance(raw_wallets, list) or not raw_wallets:
        raise DomainError("Aucun portefeuille dans les données reçues.")

    wallets = [_wallet(raw, position) for position, raw in enumerate(raw_wallets, start=1)]
    names = [w.name.casefold() for w in wallets]
    if len(set(names)) != len(names):
        raise DomainError("Deux portefeuilles reçus portent le même nom.")
    active = next((w.name for w in wallets if w.id == payload.get("activeWalletId")), wallets[0].name)
    return Reception(tuple(wallets), active)


def new_transactions(existing: Ledger, incoming: Ledger) -> list[Transaction]:
    """Transactions de `incoming` absentes de `existing` (comparaison par contenu, doublons exacts comptés).

    Recevoir deux fois les mêmes données ne crée donc rien de plus. Une suppression faite côté émetteur
    n'est pas répercutée : il s'agit d'une fusion, pas d'un remplacement.
    """
    available = Counter(existing.transactions)
    fresh = []
    for transaction in incoming.transactions:
        if available[transaction] > 0:
            available[transaction] -= 1
        else:
            fresh.append(transaction)
    return fresh


# ---- validation ---------------------------------------------------------------------------------------
def _as_object(data) -> dict:
    if isinstance(data, (str, bytes, bytearray)):
        try:
            data = json.loads(data)
        except ValueError as e:   # JSON invalide ou octets non décodables
            raise DomainError("Données reçues illisibles : JSON invalide.") from e
    if not isinstance(data, dict):
        raise DomainError("Données reçues invalides : un objet JSON est attendu.")
    return data


def _whole(value, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not float(value).is_integer():
        raise DomainError(f"{where} : nombre entier attendu (reçu : {value!r}).")
    return int(value)


def _text(value, where: str, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise DomainError(f"{where} : texte {'non vide ' if required else ''}attendu.")
    return value.strip()


def _objects(raw: dict, key: str, where: str) -> list[dict]:
    items = raw.get(key, [])
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise DomainError(f"{where} : « {key} » doit être une liste d'objets.")
    return items


def _wallet(raw, position: int) -> ReceivedWallet:
    if not isinstance(raw, dict):
        raise DomainError(f"Portefeuille n°{position} : objet attendu.")
    name = _text(raw.get("name"), f"Portefeuille n°{position}, nom")
    where = f"Portefeuille « {name} »"
    initial = _whole(raw.get("initialBalance", 0), f"{where}, solde initial")

    categories, budgets, warnings = [], {}, []
    for number, item in enumerate(_objects(raw, "categories", where), start=1):
        label = f"{where}, catégorie n°{number}"
        category = _text(item.get("name"), f"{label}, nom")
        budget = _whole(item.get("dailyBudget", 0), f"{label}, budget par jour")
        if budget < 0:
            raise DomainError(f"{label} : le budget par jour ne peut pas être négatif.")
        opening = _whole(item.get("initialBalance", 0), f"{label}, solde de départ")
        categories.append(category)
        if budget > 0:
            budgets[category] = budget
        if opening != 0:
            warnings.append(f"{where} : le solde de départ de la catégorie « {category} » ({opening}) "
                            "n'est pas repris (non géré par l'application).")

    transactions = []
    for number, item in enumerate(_objects(raw, "transactions", where), start=1):
        label = f"{where}, transaction n°{number}"
        date = item.get("date")
        if not isinstance(date, str) or not _DATE.match(date):
            raise DomainError(f"{label} : date invalide (format AAAA-MM-JJ attendu).")
        try:
            day = dt.date.fromisoformat(date)
        except ValueError as e:
            raise DomainError(f"{label} : date inexistante ({date}).") from e
        kind = _KINDS.get(item.get("kind"))
        if kind is None:
            raise DomainError(f"{label} : type inconnu (attendu : deposit ou expense).")
        amount = _whole(item.get("amount"), f"{label}, montant")
        if amount <= 0:
            raise DomainError(f"{label} : le montant doit être positif.")
        transactions.append(Transaction(day, _text(item.get("category"), f"{label}, catégorie"), kind,
                                        _text(item.get("label"), f"{label}, libellé", required=False), amount))

    return ReceivedWallet(str(raw.get("id") or ""), name, Ledger(transactions, initial, categories, budgets),
                          tuple(warnings))
