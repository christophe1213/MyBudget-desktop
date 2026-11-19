from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager

from .....application.errors import StorageError
from .....application.events import Event
from .....application.ports.inbound import EventSource
from .....domain.model.errors import DomainError
from ..contract.interfaces import Dialogs
from ..parsing import InvalidInput


class Controller(ABC):
    """Base des contrôleurs : abonnement aux changements et gestion uniforme des erreurs.

    Un contrôleur traduit les actions de l'utilisateur en appels aux PORTS ENTRANTS de l'application,
    et les résultats en affichage pour sa vue. Il n'importe ni tkinter, ni Excel, ni pandas.
    """

    def __init__(self, events: EventSource, dialogs: Dialogs):
        self._events = events
        self._dialogs = dialogs

    def start(self) -> None:
        self._events.subscribe(self._on_event)
        self.refresh()

    # ---- réactions aux événements de l'application -------------------------------------------
    def _on_event(self, event: Event) -> None:
        if event is Event.WALLET_CHANGED:
            self.on_wallet_changed()
        elif event is Event.CATALOG_CHANGED:
            self.on_catalog_changed()
        elif event is Event.DATA_CHANGED:
            self.on_data_changed()
        elif event is Event.DATA_IMPORTED:
            self.on_imported()
        elif event is Event.BUDGETS_CHANGED:
            self.on_budgets_changed()

    def on_wallet_changed(self) -> None:
        self.reset()
        self.refresh()

    def on_data_changed(self) -> None:
        self.refresh()

    def on_imported(self) -> None:
        self.on_data_changed()

    def on_catalog_changed(self) -> None:
        """Par défaut, un changement de la liste des portefeuilles n'intéresse pas le contrôleur."""

    def on_budgets_changed(self) -> None:
        """Par défaut, un changement de budget par jour n'intéresse pas le contrôleur."""

    def reset(self) -> None:
        """Oublie l'état propre au portefeuille précédent (périodes, résultats...)."""

    @abstractmethod
    def refresh(self) -> None:
        """Remet la vue à jour à partir de l'application."""

    # ---- erreurs ---------------------------------------------------------------------------------
    @contextmanager
    def guard(self, title: str = "Erreur"):
        """Transforme les erreurs en messages pour l'utilisateur (aucune exception ne remonte)."""
        try:
            yield
        except (DomainError, InvalidInput) as e:
            self._dialogs.warning(title, str(e))
        except StorageError as e:
            self._dialogs.error("Fichier verrouillé" if e.locked else title, str(e))
        except Exception as e:  # noqa: BLE001
            self._dialogs.error(title, str(e))
