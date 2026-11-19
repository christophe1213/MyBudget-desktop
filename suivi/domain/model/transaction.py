"""Transaction : une entrée (dépôt) ou une sortie (dépense) d'argent sur une catégorie."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum


class Kind(str, Enum):
    EXPENSE = "dépense"
    DEPOSIT = "dépôt"


@dataclass(frozen=True)
class Transaction:
    date: dt.date
    category: str
    kind: Kind
    label: str
    amount: int  # en Ariary, toujours positif ; le sens est donné par `kind`

    @property
    def signed_amount(self) -> int:
        return self.amount if self.kind is Kind.DEPOSIT else -self.amount
