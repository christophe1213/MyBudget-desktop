"""Hachage des mots de passe avec scrypt (bibliothèque standard : aucune dépendance en plus).

Format : scrypt$N$r$p$sel$empreinte (base64). Chaque empreinte a son propre sel aléatoire ;
les paramètres sont stockés avec elle, on pourra donc les durcir plus tard sans casser les anciens comptes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from ...application.ports.outbound import PasswordHasher


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


class ScryptPasswordHasher(PasswordHasher):
    def __init__(self, n: int = 2 ** 14, r: int = 8, p: int = 1):
        self._n, self._r, self._p = n, r, p

    def hash(self, secret: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=self._n, r=self._r, p=self._p, dklen=32)
        return f"scrypt${self._n}${self._r}${self._p}${_b64(salt)}${_b64(digest)}"

    def verify(self, secret: str, hashed: str) -> bool:
        try:
            scheme, n, r, p, salt, expected = hashed.split("$")
            if scheme != "scrypt":
                return False
            digest = hashlib.scrypt(secret.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r),
                                    p=int(p), dklen=32)
            return hmac.compare_digest(digest, base64.b64decode(expected))
        except (ValueError, TypeError):
            return False
