from __future__ import annotations

import dataclasses
import datetime as dt
import math
import secrets
from typing import Optional

from ...domain.model.account import (Account, check_display_name, check_password, normalize_email,
                                     normalize_recovery_key)
from ...domain.model.errors import AuthenticationError, DomainError
from ..dto import LocalSession, Registration, UserInfo
from ..ports.inbound import Authenticate
from ..ports.outbound import (AccountRepository, Clock, LocalSessionStore, PasswordHasher, RememberTokens)

MAX_FAILURES = 5          # échecs consécutifs avant verrouillage
LOCK_MINUTES = 5
REMEMBER_DAYS = 30
_BAD_CREDENTIALS = "E-mail ou mot de passe incorrect."


class AuthService(Authenticate):
    """Création de compte, connexion, « Rester connecté », réinitialisation par clé de récupération.

    Les mots de passe ne sont jamais conservés : seule l'empreinte produite par le PasswordHasher l'est.
    """

    def __init__(self, accounts: AccountRepository, hasher: PasswordHasher, tokens: RememberTokens,
                 local: LocalSessionStore, clock: Clock):
        self._accounts, self._hasher, self._tokens = accounts, hasher, tokens
        self._local, self._clock = local, clock
        self._current: Optional[UserInfo] = None
        self._failures: dict[str, tuple[int, Optional[dt.datetime]]] = {}   # e-mail -> (échecs, verrouillé jusqu'à)
        self._unknown_account_hash = hasher.hash(secrets.token_hex(8))      # pour garder un temps de réponse constant

    # ---- consultation -----------------------------------------------------------------------------
    def has_accounts(self) -> bool:
        return self._accounts.count() > 0

    def last_known_name(self) -> Optional[str]:
        return self._local.load().last_name

    def last_known_email(self) -> Optional[str]:
        return self._local.load().last_email

    def current_user(self) -> Optional[UserInfo]:
        return self._current

    # ---- ouverture de session -----------------------------------------------------------------------
    def resume(self) -> Optional[UserInfo]:
        session = self._local.load()
        if not session.token:
            return None
        account_id = self._tokens.resolve(session.token, self._clock.now())
        account = self._accounts.by_id(account_id) if account_id is not None else None
        if account is None:   # jeton expiré, révoqué ou compte disparu : on l'oublie
            self._local.save(dataclasses.replace(session, token=None))
            return None
        return self._open(account)

    def login(self, email: str, password: str, remember: bool) -> UserInfo:
        email = normalize_email(email)
        self._check_not_locked(email)
        account = self._accounts.by_email(email)
        valid = self._hasher.verify(password or "", account.password_hash if account else self._unknown_account_hash)
        if account is None or not valid:
            self._record_failure(email)
            raise AuthenticationError(_BAD_CREDENTIALS)   # même message dans les deux cas : on ne révèle pas si le compte existe
        self._failures.pop(email, None)
        user = self._open(account)
        token = None
        if remember:
            token = self._tokens.issue(account.id, self._clock.now() + dt.timedelta(days=REMEMBER_DAYS))
        else:
            self._revoke_stored_token()
        self._local.save(LocalSession(token, account.email, account.name))
        return user

    def register(self, name: str, email: str, password: str, confirmation: str) -> Registration:
        name, email = check_display_name(name), normalize_email(email)
        if password != confirmation:
            raise DomainError("Les mots de passe ne correspondent pas.")
        check_password(password, email)
        if self._accounts.by_email(email) is not None:
            raise DomainError("Un compte existe déjà avec cette adresse e-mail.")
        key = self._new_recovery_key()
        account = self._accounts.add(Account(None, email, name, self._hasher.hash(password),
                                             self._hasher.hash(normalize_recovery_key(key)), self._clock.now()))
        self._revoke_stored_token()
        self._local.save(LocalSession(None, account.email, account.name))
        return Registration(self._open(account), key)

    def reset_password(self, email: str, recovery_key: str, new_password: str) -> str:
        email = normalize_email(email)
        self._check_not_locked(email)
        account = self._accounts.by_email(email)
        valid = self._hasher.verify(normalize_recovery_key(recovery_key),
                                    account.recovery_hash if account else self._unknown_account_hash)
        if account is None or not valid:
            self._record_failure(email)
            raise AuthenticationError("E-mail ou clé de récupération incorrect.")
        check_password(new_password, email)
        new_key = self._new_recovery_key()
        self._accounts.update(dataclasses.replace(
            account, password_hash=self._hasher.hash(new_password),
            recovery_hash=self._hasher.hash(normalize_recovery_key(new_key))))
        self._tokens.revoke_all(account.id)   # toutes les sessions « Rester connecté » deviennent invalides
        self._failures.pop(email, None)
        session = self._local.load()
        self._local.save(dataclasses.replace(session, token=None))
        return new_key

    def logout(self) -> None:
        self._revoke_stored_token()
        self._current = None

    # ---- interne ---------------------------------------------------------------------------------------
    def _open(self, account: Account) -> UserInfo:
        self._current = UserInfo(account.id, account.email, account.name)
        return self._current

    def _revoke_stored_token(self) -> None:
        session = self._local.load()
        if session.token:
            self._tokens.revoke(session.token)
            self._local.save(dataclasses.replace(session, token=None))

    @staticmethod
    def _new_recovery_key() -> str:
        raw = secrets.token_hex(8).upper()
        return "-".join(raw[i:i + 4] for i in range(0, 16, 4))

    def _check_not_locked(self, email: str) -> None:
        _count, until = self._failures.get(email, (0, None))
        now = self._clock.now()
        if until is not None and now < until:
            minutes = max(1, math.ceil((until - now).total_seconds() / 60))
            raise AuthenticationError(f"Trop de tentatives. Réessayez dans {minutes} min.")

    def _record_failure(self, email: str) -> None:
        count, until = self._failures.get(email, (0, None))
        if until is not None and self._clock.now() >= until:   # le verrouillage précédent est terminé
            count, until = 0, None
        count += 1
        if count >= MAX_FAILURES:
            until = self._clock.now() + dt.timedelta(minutes=LOCK_MINUTES)
        self._failures[email] = (count, until)
