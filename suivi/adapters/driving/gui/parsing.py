"""Lecture des saisies de l'utilisateur (texte -> valeurs du domaine)."""
from __future__ import annotations

import datetime as dt

from ....domain.model.transaction import Kind


class InvalidInput(Exception):
    """Le texte saisi n'a pas le bon format (le message est destiné à l'utilisateur)."""


def parse_amount(text: str) -> int:
    """'3 200 Ar' -> 3200. Doit être un entier positif."""
    t = text.lower().replace("ar", "").replace("\u202f", "").replace("\xa0", "")
    t = t.replace(" ", "").replace(",", "").replace(".", "")
    if not t.isdigit() or int(t) <= 0:
        raise InvalidInput("Montant invalide (entier positif attendu).")
    return int(t)


def parse_non_negative_int(text: str) -> int:
    t = text.replace(" ", "").lower().replace("ar", "") or "0"
    if not t.isdigit():
        raise InvalidInput("Entrez un nombre entier.")
    return int(t)


def parse_date(text: str) -> dt.date:
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise InvalidInput("Date invalide (format attendu : JJ/MM/AAAA).")


def parse_kind(text: str) -> Kind:
    try:
        return Kind(text)
    except ValueError:
        raise InvalidInput("Type de transaction invalide.") from None
