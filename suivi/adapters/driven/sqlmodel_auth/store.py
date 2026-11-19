"""Comptes et jetons « Rester connecté » dans SQLite, via SQLModel.

Seul ce module connaît SQLModel/SQLAlchemy : pour passer à PostgreSQL ou à un autre ORM, on réécrit ce
fichier (les ports AccountRepository et RememberTokens ne changent pas).
"""
import datetime as dt
import hashlib
import secrets
from typing import Optional

from pydantic import NaiveDatetime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Field, Session, SQLModel, create_engine, delete, select

from ....application.errors import StorageError
from ....application.ports.outbound import AccountRepository, RememberTokens
from ....domain.model.account import Account
from ....domain.model.errors import DomainError


class AccountRow(SQLModel, table=True):
    __tablename__ = "accounts"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    recovery_hash: str
    created_at: NaiveDatetime   # dates locales sans fuseau, comme partout dans l'application


class RememberTokenRow(SQLModel, table=True):
    __tablename__ = "remember_tokens"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    token_hash: str = Field(index=True, unique=True)   # SHA-256 du jeton : le jeton lui-même n'est jamais stocké
    expires_at: NaiveDatetime


class AuthDatabase:
    def __init__(self, path: str):
        self.engine = create_engine(f"sqlite:///{path}")
        try:
            SQLModel.metadata.create_all(self.engine, tables=[AccountRow.__table__, RememberTokenRow.__table__])
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e

    def session(self) -> Session:
        return Session(self.engine)


def _to_account(row: AccountRow) -> Account:
    return Account(row.id, row.email, row.name, row.password_hash, row.recovery_hash, row.created_at)


class SqlModelAccountRepository(AccountRepository):
    def __init__(self, database: AuthDatabase):
        self._db = database

    def count(self) -> int:
        try:
            with self._db.session() as session:
                return len(session.exec(select(AccountRow.id)).all())
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e

    def add(self, account: Account) -> Account:
        row = AccountRow(email=account.email, name=account.name, password_hash=account.password_hash,
                         recovery_hash=account.recovery_hash, created_at=account.created_at)
        try:
            with self._db.session() as session:
                session.add(row)
                session.commit()
                session.refresh(row)
                return _to_account(row)
        except IntegrityError as e:
            raise DomainError("Un compte existe déjà avec cette adresse e-mail.") from e
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e

    def by_email(self, email: str) -> Optional[Account]:
        try:
            with self._db.session() as session:
                row = session.exec(select(AccountRow).where(AccountRow.email == email)).first()
                return _to_account(row) if row else None
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e

    def by_id(self, account_id: int) -> Optional[Account]:
        try:
            with self._db.session() as session:
                row = session.get(AccountRow, account_id)
                return _to_account(row) if row else None
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e

    def update(self, account: Account) -> None:
        try:
            with self._db.session() as session:
                row = session.get(AccountRow, account.id)
                if row is None:
                    raise DomainError("Compte introuvable.")
                row.name, row.password_hash, row.recovery_hash = account.name, account.password_hash, account.recovery_hash
                session.add(row)
                session.commit()
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SqlModelRememberTokens(RememberTokens):
    def __init__(self, database: AuthDatabase):
        self._db = database

    def issue(self, account_id: int, expires_at: dt.datetime) -> str:
        token = secrets.token_urlsafe(32)
        try:
            with self._db.session() as session:
                session.add(RememberTokenRow(account_id=account_id, token_hash=_digest(token), expires_at=expires_at))
                session.commit()
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e
        return token

    def resolve(self, token: str, now: dt.datetime) -> Optional[int]:
        try:
            with self._db.session() as session:
                session.exec(delete(RememberTokenRow).where(RememberTokenRow.expires_at <= now))   # ménage
                session.commit()
                row = session.exec(select(RememberTokenRow).where(RememberTokenRow.token_hash == _digest(token))).first()
                return row.account_id if row else None
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e

    def revoke(self, token: str) -> None:
        self._delete(RememberTokenRow.token_hash == _digest(token))

    def revoke_all(self, account_id: int) -> None:
        self._delete(RememberTokenRow.account_id == account_id)

    def _delete(self, condition) -> None:
        try:
            with self._db.session() as session:
                session.exec(delete(RememberTokenRow).where(condition))
                session.commit()
        except SQLAlchemyError as e:
            raise StorageError(f"Base des comptes inaccessible : {e}") from e
