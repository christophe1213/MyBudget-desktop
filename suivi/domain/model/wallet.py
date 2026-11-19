"""Portefeuille : un livre de comptes nommé, repéré par un emplacement de stockage opaque."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .errors import DomainError


@dataclass(frozen=True)
class WalletRef:
    name: str
    location: str  # le domaine ne sait pas ce que c'est (nom de fichier, clé en base...) : c'est l'adaptateur


@dataclass(frozen=True)
class WalletCatalog:
    """Liste immuable des portefeuilles connus et du portefeuille actif."""
    wallets: tuple[WalletRef, ...]
    active: str

    def __post_init__(self) -> None:
        if not self.wallets:
            raise DomainError("Il faut au moins un portefeuille.")
        if self.active not in self.names:
            object.__setattr__(self, "active", self.wallets[0].name)

    @property
    def names(self) -> list[str]:
        return [w.name for w in self.wallets]

    @property
    def active_ref(self) -> WalletRef:
        return self.find(self.active)

    def find(self, name: str) -> WalletRef:
        for w in self.wallets:
            if w.name == name:
                return w
        raise DomainError(f"Portefeuille « {name} » introuvable.")

    def check_name(self, name: str, ignore: Optional[str] = None) -> None:
        if not name:
            raise DomainError("Le nom ne peut pas être vide.")
        if any(w.name.casefold() == name.casefold() for w in self.wallets if w.name != ignore):
            raise DomainError(f"Un portefeuille « {name} » existe déjà.")

    def with_wallet(self, ref: WalletRef, make_active: bool = False) -> "WalletCatalog":
        self.check_name(ref.name)
        return WalletCatalog(self.wallets + (ref,), ref.name if make_active else self.active)

    def activated(self, name: str) -> "WalletCatalog":
        self.find(name)
        return WalletCatalog(self.wallets, name)

    def renamed(self, old: str, new: str) -> "WalletCatalog":
        self.check_name(new, ignore=old)
        wallets = tuple(WalletRef(new, w.location) if w.name == old else w for w in self.wallets)
        return WalletCatalog(wallets, new if self.active == old else self.active)

    def without(self, name: str) -> "WalletCatalog":
        if len(self.wallets) == 1:
            raise DomainError("Impossible de retirer le dernier portefeuille.")
        self.find(name)
        return WalletCatalog(tuple(w for w in self.wallets if w.name != name), self.active)
