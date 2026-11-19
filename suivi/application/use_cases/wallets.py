from __future__ import annotations

from ...domain.model.errors import DomainError
from ...domain.model.ledger import Ledger
from ...domain.model.wallet import WalletCatalog, WalletRef
from ...domain.services.balances import BalanceCalculator
from ..dto import WalletSummary
from ..errors import StorageError
from ..events import Event, EventEmitter
from ..ports.inbound import ManageWallets
from ..ports.outbound import LedgerRepository, LocationPolicy, WalletRegistry
from ..session import LedgerSession


class WalletsUseCase(ManageWallets):
    """Créer, associer, renommer, retirer et ouvrir des portefeuilles (le stockage n'est jamais supprimé)."""

    def __init__(self, registry: WalletRegistry, ledgers: LedgerRepository, locations: LocationPolicy,
                 balances: BalanceCalculator, session: LedgerSession, events: EventEmitter):
        self._registry = registry
        self._ledgers = ledgers
        self._locations = locations
        self._balances = balances
        self._session = session
        self._events = events
        self._catalog: WalletCatalog | None = None   # chargé par start()

    # ---- consultation --------------------------------------------------------------------
    def names(self) -> list[str]:
        return self._catalog.names

    def active_name(self) -> str:
        return self._catalog.active

    def link_patterns(self) -> tuple:
        return tuple(self._locations.link_patterns)

    def summaries(self) -> list[WalletSummary]:
        result = []
        for ref in self._catalog.wallets:
            active = ref.name == self._catalog.active
            ledger = self._session.ledger if active else self._read(ref.location)
            if ledger is None:
                result.append(WalletSummary(ref.name, ref.location, active, None, None))
            else:
                result.append(WalletSummary(ref.name, ref.location, active, len(ledger.transactions),
                                            self._balances.total(ledger)))
        return result

    def _read(self, location: str):
        if not self._ledgers.exists(location):
            return None
        try:
            return self._ledgers.load(location)
        except StorageError:
            return None

    # ---- actions ---------------------------------------------------------------------------
    def start(self) -> None:
        try:
            self._catalog = self._registry.load()
            self._registry.save(self._catalog)   # crée la liste au premier lancement
        except StorageError:
            if self._catalog is None:
                raise
        self._session.open(self._catalog.active_ref.location)

    def open(self, name: str) -> None:
        if name != self._catalog.active:
            self._switch(self._catalog.activated(name))

    def create(self, name: str) -> WalletRef:
        name = name.strip()
        self._catalog.check_name(name)
        location = self._locations.suggest_location(name, [w.location for w in self._catalog.wallets])
        self._ledgers.save(location, Ledger())
        ref = WalletRef(name, location)
        self._switch(self._catalog.with_wallet(ref, make_active=True))
        return ref

    def prepare_link(self, path: str) -> str:
        location = self._locations.location_from_path(path)
        taken = {self._locations.canonical(w.location) for w in self._catalog.wallets}
        if self._locations.canonical(location) in taken:
            raise DomainError("Ce fichier est déjà utilisé par un portefeuille.")
        try:
            self._ledgers.load(location)
        except StorageError as e:
            raise DomainError(f"Ce fichier n'est pas un fichier de transactions valide :\n{e}") from e
        return location

    def link(self, name: str, location: str) -> None:
        self._switch(self._catalog.with_wallet(WalletRef(name.strip(), location), make_active=True))

    def rename(self, old: str, new: str) -> None:
        self._catalog = self._catalog.renamed(old, new.strip())
        self._persist_and_notify()

    def remove(self, name: str) -> None:
        remaining = self._catalog.without(name)
        if name == self._catalog.active:
            self._switch(remaining)   # le premier portefeuille restant devient actif
        else:
            self._catalog = remaining
            self._persist_and_notify()

    # ---- interne ---------------------------------------------------------------------------
    def _switch(self, catalog: WalletCatalog) -> None:
        """Change de portefeuille actif ; en cas d'échec de lecture, on garde l'état précédent."""
        previous = self._catalog
        self._catalog = catalog
        try:
            self._session.open(catalog.active_ref.location)
        except Exception:
            self._catalog = previous
            raise
        self._persist_and_notify()

    def _persist_and_notify(self) -> None:
        self._registry.save(self._catalog)
        self._events.emit(Event.CATALOG_CHANGED)
