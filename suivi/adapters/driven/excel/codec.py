"""Conversion entre les lignes d'une feuille Excel et les objets du domaine."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from ....domain.model.transaction import Kind, Transaction

COLUMNS = ("date", "categorie", "type", "libelle", "montant")
_KINDS = {"dépense": Kind.EXPENSE, "depense": Kind.EXPENSE, "dépôt": Kind.DEPOSIT, "depot": Kind.DEPOSIT}
_DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d")


def normalize_header(value) -> str:
    return "" if value is None else str(value).strip().lower().replace("é", "e")


def parse_date_cell(value) -> Optional[dt.date]:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        for fmt in _DATE_FORMATS:
            try:
                return dt.datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _cell(row, index):
    return row[index] if index < len(row) else None


def read_transactions(sheet) -> list[Transaction]:
    """Lit une feuille (en-tête + lignes). Les lignes sans date ou sans montant sont ignorées."""
    rows = sheet.iter_rows(values_only=True)
    try:
        return _read_rows(rows)
    finally:
        rows.close()   # libère le flux du classeur même si une ligne est invalide


def _read_rows(rows) -> list[Transaction]:
    header = next(rows, None)
    if header is None:
        return []
    index = {normalize_header(h): i for i, h in enumerate(header)}
    missing = [c for c in COLUMNS if c not in index]
    if missing:
        raise ValueError(f"Colonnes manquantes : {', '.join(missing)}")
    result = []
    for line, row in enumerate(rows, start=2):
        date = parse_date_cell(_cell(row, index["date"]))
        raw_amount = _cell(row, index["montant"])
        if date is None or raw_amount is None:
            continue
        kind = _KINDS.get(str(_cell(row, index["type"]) or "").strip().lower())
        if kind is None:
            raise ValueError(f"Type de transaction inconnu à la ligne {line} (attendu : dépense ou dépôt).")
        amount = int(round(float(raw_amount)))
        if amount <= 0:
            raise ValueError(f"Montant invalide à la ligne {line} (entier positif attendu).")
        result.append(Transaction(
            date, str(_cell(row, index["categorie"]) or "").strip(), kind,
            str(_cell(row, index["libelle"]) or "").strip(), amount))
    return result
