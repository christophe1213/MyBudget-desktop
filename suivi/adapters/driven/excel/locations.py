from __future__ import annotations

import os
from typing import Iterable, Optional

from ....application.naming import slug
from ....application.ports.outbound import LocationPolicy


class FileLocationPolicy(LocationPolicy):
    """Un portefeuille = un classeur Excel ; l'emplacement est un nom de fichier (ou un chemin complet)."""

    link_patterns = ("*.xlsx",)

    def __init__(self, base_dir: str):
        self._base_dir = os.path.abspath(base_dir)

    def resolve(self, location: str) -> str:
        return location if os.path.isabs(location) else os.path.join(self._base_dir, location)

    def suggest_location(self, wallet_name: str, taken: Iterable[str]) -> str:
        base = f"transactions_{slug(wallet_name)}"
        used = {os.path.normcase(self.resolve(t)) for t in taken}
        candidate, n = f"{base}.xlsx", 2
        while os.path.normcase(self.resolve(candidate)) in used or os.path.exists(self.resolve(candidate)):
            candidate, n = f"{base}_{n}.xlsx", n + 1
        return candidate

    def location_from_path(self, path: str) -> str:
        path = os.path.abspath(path)
        if os.path.normcase(os.path.dirname(path)) == os.path.normcase(self._base_dir):
            return os.path.basename(path)
        return path

    def canonical(self, location: str) -> str:
        return os.path.normcase(os.path.abspath(self.resolve(location)))

    def storage_path(self, location: str) -> Optional[str]:
        return self.resolve(location)
