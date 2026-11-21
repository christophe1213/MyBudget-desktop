"""Journal de synchronisation : un fichier texte (UTF-8), une ligne par événement, ajoutées à la fin."""
from __future__ import annotations

from ...application.errors import StorageError
from ...application.ports.outbound import SyncJournal


class TextSyncJournal(SyncJournal):
    def __init__(self, path: str):
        self._path = path

    @property
    def location(self) -> str:
        return self._path

    def append(self, line: str) -> None:
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            raise StorageError(f"Journal de synchronisation illisible ou protégé : {e}") from e

    def tail(self, count: int) -> list[str]:
        if count <= 0:
            return []
        try:
            with open(self._path, encoding="utf-8", errors="replace") as f:
                return f.read().splitlines()[-count:]
        except FileNotFoundError:
            return []
        except OSError as e:
            raise StorageError(f"Journal de synchronisation illisible : {e}") from e
