"""JSON « repere » -> classeurs Excel : écrit chaque portefeuille reçu dans son propre fichier .xlsx.

Les classeurs sont écrits par le MÊME adaptateur que l'application (`ExcelLedgerRepository`) : ils s'ouvrent
ensuite tels quels dans Repère. Le nom du fichier suit la convention de l'application
(`transactions_<portefeuille>.xlsx`) et un fichier existant n'est JAMAIS écrasé : le nouveau reçoit un
suffixe (`_2`, `_3`...).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Union

from ....application.errors import StorageError
from ....application.repere_import import repere_to_ledgers
from ....domain.model.errors import DomainError
from ....domain.services.balances import BalanceCalculator
from .locations import FileLocationPolicy
from .repository import ExcelLedgerRepository


@dataclass(frozen=True)
class XlsxConversion:
    files: tuple[tuple[str, str], ...]   # (nom du portefeuille, chemin du classeur écrit)
    warnings: tuple[str, ...]            # données non reprises (à montrer à l'utilisateur)


def repere_to_xlsx(data: Union[dict, str, bytes], directory: str, wallet: Optional[str] = None) -> XlsxConversion:
    """Écrit les portefeuilles de `data` dans `directory` (créé au besoin), un classeur chacun.

    `wallet` : nom ou identifiant d'un portefeuille (défaut : tous).
    Lève DomainError si les données sont invalides, StorageError si l'écriture échoue.
    """
    reception = repere_to_ledgers(data)   # tout est validé avant d'écrire le moindre fichier
    selected = [w for w in reception.wallets if wallet is None or wallet in (w.name, w.id)]
    if not selected:
        raise DomainError(f"Portefeuille « {wallet} » introuvable. Portefeuilles : "
                          f"{', '.join(w.name for w in reception.wallets)}.")
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as e:
        raise StorageError(f"Impossible de créer le dossier {directory} : {e}") from e

    locations = FileLocationPolicy(directory)
    repository = ExcelLedgerRepository(locations, BalanceCalculator())
    files = []
    for received in selected:
        location = locations.suggest_location(received.name, [])   # un nom libre : aucun fichier écrasé
        repository.save(location, received.ledger)
        files.append((received.name, locations.resolve(location)))
    return XlsxConversion(tuple(files), tuple(w for r in selected for w in r.warnings))


def repere_file_to_xlsx(path: str, directory: Optional[str] = None, wallet: Optional[str] = None) -> XlsxConversion:
    """Même conversion depuis un fichier .json ; `directory` : dossier de sortie (défaut : celui du fichier)."""
    try:
        with open(path, "rb") as f:
            content = f.read()
    except OSError as e:
        raise StorageError(f"Impossible de lire {path} : {e}") from e
    return repere_to_xlsx(content, directory or os.path.dirname(os.path.abspath(path)), wallet)
