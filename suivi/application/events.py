"""Notifications émises par l'application vers les adaptateurs d'interface (patron Observateur)."""
from __future__ import annotations

from enum import Enum, auto
from typing import Callable

from .ports.inbound import EventSource


class Event(Enum):
    WALLET_CHANGED = auto()    # un autre portefeuille a été ouvert
    CATALOG_CHANGED = auto()   # la liste des portefeuilles (ou le portefeuille actif) a changé
    DATA_CHANGED = auto()      # transactions, catégories ou solde initial modifiés
    DATA_IMPORTED = auto()     # transactions importées (comme DATA_CHANGED + périodes à réinitialiser)
    BUDGETS_CHANGED = auto()   # seuls les budgets par jour ont changé


class EventEmitter(EventSource):
    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        self._subscribers.append(callback)

    def emit(self, event: Event) -> None:
        for callback in list(self._subscribers):
            callback(event)
