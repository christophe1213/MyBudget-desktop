"""Format d'échange « repere » (version 1) : conversion des livres de comptes vers un dictionnaire JSON.

Python pur (aucune dépendance à Excel ni au réseau) : le serveur de synchronisation, un export manuel ou
un test peuvent tous l'utiliser. Les identifiants sont DÉTERMINISTES : exporter deux fois le même contenu
donne les mêmes identifiants, ce qui permet à l'appareil qui reçoit de fusionner au lieu de dupliquer.

Structure produite :
    {"format": "repere", "version": 1, "exportedAt": "...Z", "activeWalletId": "...",
     "wallets": [{"id", "name", "initialBalance",
                  "categories": [{"name", "dailyBudget", "initialBalance"}],
                  "transactions": [{"id", "date", "category", "kind", "label", "amount"}]}]}
"""
from __future__ import annotations

import datetime as dt
import hashlib
import string
from collections import Counter
from typing import Optional, Sequence

from ..domain.model.errors import DomainError
from ..domain.model.ledger import Ledger
from ..domain.model.transaction import Kind

FORMAT_NAME = "repere"
FORMAT_VERSION = 1

_KIND_CODES = {Kind.DEPOSIT: "deposit", Kind.EXPENSE: "expense"}
_BASE36 = string.digits + string.ascii_lowercase


def _to_base36(n: int) -> str:
    digits = ""
    while n:
        n, r = divmod(n, 36)
        digits = _BASE36[r] + digits
    return digits or "0"


def stable_id(*parts: object) -> str:
    """Identifiant `id-xxxxxxxx-xxxxxxxx` calculé à partir du contenu (même entrée -> même identifiant)."""
    digest = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).digest()
    text = _to_base36(int.from_bytes(digest[:10], "big")).rjust(16, "0")
    return f"id-{text[:8]}-{text[8:]}"


def _timestamp(moment: Optional[dt.datetime]) -> str:
    moment = (moment or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)   # naïf = heure locale
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def ledger_to_repere_wallet(name: str, ledger: Ledger, start: Optional[dt.date] = None) -> dict:
    """Un portefeuille au format « repere ».

    Avec `start`, seules les transactions à partir de cette date sont exportées ; les précédentes sont
    reportées dans le solde de départ (`initialBalance`) de leur catégorie (dépôts − dépenses).
    """
    wallet_id = stable_id("wallet", name)
    transactions = sorted(ledger.transactions, key=lambda t: t.date)   # tri stable par date
    before = [t for t in transactions if start is not None and t.date < start]
    kept = [t for t in transactions if start is None or t.date >= start]

    carried: Counter = Counter()
    for t in before:
        carried[t.category] += t.signed_amount

    names = ledger.categories + sorted({t.category for t in transactions} - set(ledger.categories))
    seen: Counter = Counter()
    exported = []
    for t in kept:
        key = (t.date.isoformat(), t.category, t.kind.value, t.label, t.amount)
        exported.append({
            "id": stable_id(wallet_id, *key, seen[key]),   # le rang distingue deux lignes identiques
            "date": t.date.isoformat(),
            "category": t.category,
            "kind": _KIND_CODES[t.kind],
            "label": t.label,
            "amount": t.amount,
        })
        seen[key] += 1

    return {
        "id": wallet_id,
        "name": name,
        "initialBalance": ledger.initial_balance,
        "categories": [{"name": c, "dailyBudget": ledger.daily_budget(c), "initialBalance": carried[c]}
                       for c in names],
        "transactions": exported,
    }


def ledgers_to_repere(wallets: Sequence[tuple[str, Ledger]], active: Optional[str] = None,
                      start: Optional[dt.date] = None, exported_at: Optional[dt.datetime] = None) -> dict:
    """Export complet : une liste de (nom du portefeuille, livre). `active` : nom du portefeuille actif."""
    if not wallets:
        raise DomainError("Aucun portefeuille à exporter.")
    names = [n for n, _ in wallets]
    if len(set(names)) != len(names):
        raise DomainError("Deux portefeuilles portent le même nom.")
    if active is not None and active not in names:
        raise DomainError(f"Portefeuille « {active} » introuvable.")
    items = [ledger_to_repere_wallet(n, ledger, start) for n, ledger in wallets]
    active_item = items[names.index(active)] if active is not None else items[0]
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "exportedAt": _timestamp(exported_at),
        "activeWalletId": active_item["id"],
        "wallets": items,
    }
