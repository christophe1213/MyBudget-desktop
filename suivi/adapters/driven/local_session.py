"""Mémoire locale entre deux lancements : jeton « Rester connecté » et dernier utilisateur (fichier JSON)."""
from __future__ import annotations

import json
import os

from ...application.dto import LocalSession
from ...application.errors import StorageError
from ...application.ports.outbound import LocalSessionStore


class JsonFileLocalSessionStore(LocalSessionStore):
    def __init__(self, path: str):
        self._path = path

    def load(self) -> LocalSession:
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            return LocalSession(data.get("token"), data.get("last_email"), data.get("last_name"))
        except (OSError, ValueError, AttributeError):
            return LocalSession()   # fichier absent ou illisible : on repart de zéro (l'utilisateur se reconnectera)

    def save(self, session: LocalSession) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({"token": session.token, "last_email": session.last_email,
                           "last_name": session.last_name}, f)
            try:
                os.chmod(self._path, 0o600)   # le jeton est un secret : lecture réservée au propriétaire
            except OSError:
                pass
        except OSError as e:
            raise StorageError(f"Impossible d'enregistrer la session locale : {e}") from e
