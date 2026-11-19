from __future__ import annotations

from typing import Callable

from ..domain.model.ledger import Ledger
from .events import Event, EventEmitter
from .ports.outbound import LedgerRepository


class LedgerSession:
    """Le livre de comptes actuellement ouvert.

    Toute modification passe par `apply` : on travaille sur une copie, on l'enregistre, puis on la
    substitue à l'original. Si la règle métier ou l'enregistrement échoue, rien n'a changé.
    """

    def __init__(self, repository: LedgerRepository, events: EventEmitter):
        self._repository = repository
        self._events = events
        self._ledger = Ledger()
        self._location: str | None = None

    @property
    def ledger(self) -> Ledger:
        """Lecture seule : ne jamais modifier directement (utiliser `apply`)."""
        return self._ledger

    @property
    def location(self) -> str:
        if self._location is None:
            raise RuntimeError("Aucun portefeuille ouvert.")
        return self._location

    def open(self, location: str) -> None:
        ledger = self._repository.load(location)   # si ça échoue, l'état actuel est conservé
        self._ledger, self._location = ledger, location
        self._events.emit(Event.WALLET_CHANGED)

    def apply(self, mutator: Callable[[Ledger], object], event: Event = Event.DATA_CHANGED):
        new = self._ledger.copy()
        result = mutator(new)
        self._repository.save(self.location, new)
        self._ledger = new
        self._events.emit(event)
        return result

    def ensure_saved(self) -> str:
        """S'assure que le portefeuille existe dans le stockage ; retourne son emplacement."""
        if not self._repository.exists(self.location):
            self._repository.save(self.location, self._ledger)
        return self.location
