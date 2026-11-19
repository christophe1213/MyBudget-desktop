"""Aides partagées par les vues (indépendantes de la bibliothèque graphique)."""
from __future__ import annotations

from typing import Callable


def call(listener_getter: Callable[[], object], method: str, *args) -> None:
    """Appelle `listener.method(*args)` si un écouteur est branché (évite les erreurs au démarrage)."""
    listener = listener_getter()
    if listener is not None:
        getattr(listener, method)(*args)
