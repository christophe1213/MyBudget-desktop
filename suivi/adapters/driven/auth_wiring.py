"""Lot d'adaptateurs de l'authentification : comptes dans SQLite (SQLModel), session locale en JSON."""
from __future__ import annotations

import os

from ...application.ports.outbound import AuthPorts
from .local_session import JsonFileLocalSessionStore
from .security import ScryptPasswordHasher
from .sqlmodel_auth.store import AuthDatabase, SqlModelAccountRepository, SqlModelRememberTokens


def sqlmodel_auth_ports(data_dir: str) -> AuthPorts:
    database = AuthDatabase(os.path.join(data_dir, "comptes.db"))
    return AuthPorts(accounts=SqlModelAccountRepository(database), hasher=ScryptPasswordHasher(),
                     tokens=SqlModelRememberTokens(database),
                     local=JsonFileLocalSessionStore(os.path.join(data_dir, "session.json")))
