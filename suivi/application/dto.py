"""Objets de transfert entre l'application et les adaptateurs (données simples, sans logique)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..domain.model.transaction import Transaction


@dataclass(frozen=True)
class CategoryInfo:
    name: str
    usage: int           # nombre de transactions de la catégorie
    daily_budget: int    # 0 = pas de budget par jour


@dataclass(frozen=True)
class WalletSummary:
    name: str
    location: str
    active: bool
    transaction_count: Optional[int]   # None : stockage introuvable ou illisible
    balance: Optional[int]


@dataclass(frozen=True)
class ImportPreview:
    transactions: tuple[Transaction, ...]
    new_categories: tuple[str, ...]


@dataclass(frozen=True)
class UserInfo:
    """Ce que l'interface a le droit de savoir d'un utilisateur connecté (jamais de mot de passe ni d'empreinte)."""
    id: int
    email: str
    name: str


@dataclass(frozen=True)
class Registration:
    user: UserInfo
    recovery_key: str   # affichée UNE seule fois à la création du compte


@dataclass(frozen=True)
class LocalSession:
    """Ce que le poste mémorise entre deux lancements."""
    token: Optional[str] = None        # jeton « Rester connecté » (secret)
    last_email: Optional[str] = None   # pour préremplir et saluer (non secret)
    last_name: Optional[str] = None
