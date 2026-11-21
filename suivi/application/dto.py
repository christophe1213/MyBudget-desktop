"""Objets de transfert entre l'application et les adaptateurs (données simples, sans logique)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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


class WalletSyncStatus(Enum):
    MERGED = "fusionné"
    UNCHANGED = "déjà à jour"
    UNKNOWN_WALLET = "portefeuille inconnu ici (ignoré)"
    FAILED = "échec"


@dataclass(frozen=True)
class SyncWalletPreview:
    """Ce qu'une synchronisation fera à UN portefeuille, pour que l'utilisateur confirme avant d'agir."""
    name: str
    transactions: tuple[Transaction, ...] = ()           # à envoyer, ou nouvelles à ajouter
    already_present: int = 0                             # réception : reçues mais déjà connues
    new_categories: tuple[str, ...] = ()                 # réception : catégories qui seront créées
    opening_balances: tuple[tuple[str, int], ...] = ()   # envoi : soldes de départ reportés (catégorie, montant)
    status: Optional[WalletSyncStatus] = None            # réception : inconnu ici / échec ; None = normal
    detail: str = ""


@dataclass(frozen=True)
class SyncPreview:
    """Aperçu d'une réception : rien n'a encore été modifié."""
    wallets: tuple[SyncWalletPreview, ...]
    warnings: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        return any(w.transactions or w.new_categories for w in self.wallets)


@dataclass(frozen=True)
class SyncExport:
    """Données prêtes à être envoyées à un appareil (format « repere »)."""
    payload: dict
    wallets: int
    transactions: int
    skipped: tuple[str, ...] = ()      # portefeuilles illisibles, non exportés
    details: tuple[SyncWalletPreview, ...] = ()   # la liste exacte de ce qui sera envoyé, par portefeuille


@dataclass(frozen=True)
class WalletSyncResult:
    name: str
    status: WalletSyncStatus
    added: int = 0                     # transactions ajoutées
    already_present: int = 0           # transactions reçues mais déjà connues
    detail: str = ""                   # explication en cas d'échec


@dataclass(frozen=True)
class SyncReport:
    """Résultat de la réception de données : une ligne par portefeuille reçu."""
    results: tuple[WalletSyncResult, ...]
    warnings: tuple[str, ...] = ()     # données non reprises (voir repere_import)
