"""Excel -> JSON « repere » : lit un classeur de caisse et le convertit pour la synchronisation.

Le classeur est relu par le MÊME adaptateur que l'application (`ExcelLedgerRepository`) : mêmes feuilles
(Transactions, Catégories, Paramètres), mêmes formats de date, mêmes contrôles. La conversion elle-même
est dans `application/repere_format.py` (Python pur).
"""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import Optional

from ....application.errors import StorageError
from ....application.repere_format import ledgers_to_repere
from ....domain.services.balances import BalanceCalculator
from .locations import FileLocationPolicy
from .repository import ExcelLedgerRepository


def xlsx_to_repere(path: str, wallet_name: Optional[str] = None, start: Optional[dt.date] = None,
                   exported_at: Optional[dt.datetime] = None) -> dict:
    """Convertit un classeur .xlsx en dictionnaire « repere » (un portefeuille).

    `wallet_name` : nom du portefeuille (défaut : nom du fichier sans extension).
    `start` : date de début ; ce qui précède est reporté dans les soldes de départ des catégories.
    Lève StorageError si le fichier est introuvable, verrouillé ou invalide.
    """
    full_path = os.path.abspath(path)
    if not os.path.isfile(full_path):
        raise StorageError(f"Fichier introuvable : {path}")
    repository = ExcelLedgerRepository(FileLocationPolicy(os.path.dirname(full_path)), BalanceCalculator())
    ledger = repository.load(full_path)
    name = wallet_name or os.path.splitext(os.path.basename(full_path))[0]
    return ledgers_to_repere([(name, ledger)], start=start, exported_at=exported_at)


def xlsx_to_repere_json(path: str, wallet_name: Optional[str] = None, start: Optional[dt.date] = None,
                        exported_at: Optional[dt.datetime] = None) -> str:
    """Même conversion, retournée en texte JSON (UTF-8, accents conservés) prêt à être envoyé."""
    return json.dumps(xlsx_to_repere(path, wallet_name, start, exported_at), ensure_ascii=False, indent=2)
