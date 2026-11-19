"""Compte utilisateur et règles d'identité (Python pur : aucune notion de base de données ni de hachage)."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Optional

from .errors import DomainError

MIN_PASSWORD_LENGTH = 8
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Account:
    id: Optional[int]          # None tant que le compte n'est pas enregistré
    email: str                 # toujours normalisé (minuscules, sans espaces)
    name: str
    password_hash: str         # résultat d'un PasswordHasher : le domaine ne sait pas comment il est produit
    recovery_hash: str         # empreinte de la clé de récupération
    created_at: dt.datetime


def normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not _EMAIL.match(email):
        raise DomainError("Adresse e-mail invalide.")
    return email


def check_display_name(raw: str) -> str:
    name = " ".join((raw or "").split())
    if not name:
        raise DomainError("Indiquez votre nom.")
    if len(name) > 60:
        raise DomainError("Le nom est trop long (60 caractères maximum).")
    return name


def check_password(password: str, email: str = "") -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise DomainError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    if password.strip().lower() == email.lower() or len(set(password)) == 1:
        raise DomainError("Ce mot de passe est trop facile à deviner.")


def normalize_recovery_key(raw: str) -> str:
    """'a1b2-c3d4 e5f6' -> 'A1B2C3D4E5F6' : tolère les tirets, espaces et la casse à la saisie."""
    return re.sub(r"[\s-]", "", raw or "").upper()
