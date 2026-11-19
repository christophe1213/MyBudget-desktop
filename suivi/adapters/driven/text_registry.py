"""Liste des portefeuilles dans un fichier texte :

    #actif=Caisse
    Principal;transactions.xlsx
    Banque;transactions_banque.xlsx

Les contraintes de CE format (séparateur « ; », lignes « # ») sont gérées ici par échappement : le
domaine n'a pas à les connaître.
"""
from __future__ import annotations

import os
import re

from ...application.errors import StorageError
from ...application.ports.outbound import WalletRegistry
from ...domain.model.wallet import WalletCatalog, WalletRef

_ESCAPES = {"%": "%25", ";": "%3B", "#": "%23", "\n": "%0A", "\r": "%0D"}
_UNESCAPE = re.compile(r"%25|%3B|%23|%0A|%0D")
_REVERSE = {v: k for k, v in _ESCAPES.items()}


def _escape(text: str) -> str:
    return "".join(_ESCAPES.get(ch, ch) for ch in text)


def _unescape(text: str) -> str:
    return _UNESCAPE.sub(lambda m: _REVERSE[m.group(0)], text)


class TextFileWalletRegistry(WalletRegistry):
    def __init__(self, base_dir: str, filename: str, default: WalletRef):
        self._path = os.path.join(base_dir, filename)
        self._default = default

    def load(self) -> WalletCatalog:
        wallets: list[WalletRef] = []
        active = None
        try:
            if os.path.exists(self._path):
                with open(self._path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#actif="):
                            active = _unescape(line[len("#actif="):].strip())
                        elif line and not line.startswith("#") and ";" in line:
                            name, location = line.split(";", 1)
                            if name.strip() and location.strip():
                                wallets.append(WalletRef(_unescape(name.strip()), location.strip()))
        except OSError as e:
            raise StorageError(f"Impossible de lire {self._path} : {e}") from e
        return WalletCatalog(tuple(wallets) or (self._default,), active or "")

    def save(self, catalog: WalletCatalog) -> None:
        lines = ["# Portefeuilles : une ligne 'nom;fichier.xlsx' par portefeuille",
                 f"#actif={_escape(catalog.active)}"]
        lines += [f"{_escape(w.name)};{w.location}" for w in catalog.wallets]
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except OSError as e:
            raise StorageError(f"Impossible d'écrire {os.path.basename(self._path)} : {e}") from e
