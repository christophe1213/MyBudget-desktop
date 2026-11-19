"""Les vrais adaptateurs d'authentification : scrypt, SQLModel + SQLite, session locale JSON."""
import datetime as dt
import os
import sqlite3
import stat
import sys
import tempfile
import unittest

from suivi.adapters.driven.auth_wiring import sqlmodel_auth_ports
from suivi.adapters.driven.local_session import JsonFileLocalSessionStore
from suivi.adapters.driven.security import ScryptPasswordHasher
from suivi.adapters.driven.sqlmodel_auth.store import AuthDatabase, SqlModelAccountRepository, SqlModelRememberTokens
from suivi.application.dto import LocalSession
from suivi.domain.model.account import Account
from suivi.domain.model.errors import DomainError

NOW = dt.datetime(2026, 10, 1, 9, 0)


def account(email="rina@exemple.fr", name="Rina"):
    return Account(None, email, name, "hash-mdp", "hash-cle", NOW)


class HasherTest(unittest.TestCase):
    def test_hachage_verification_et_sel(self):
        hasher = ScryptPasswordHasher()
        first, second = hasher.hash("motdepasse1"), hasher.hash("motdepasse1")
        self.assertNotEqual(first, second)                              # sel aléatoire propre à chaque empreinte
        self.assertTrue(first.startswith("scrypt$16384$8$1$"))          # paramètres conservés avec l'empreinte
        self.assertTrue(hasher.verify("motdepasse1", first))
        self.assertFalse(hasher.verify("motdepasse2", first))

    def test_empreintes_invalides_refusees_sans_erreur(self):
        hasher = ScryptPasswordHasher()
        for garbage in ("", "n'importe quoi", "bcrypt$1$2$3$a$b", "scrypt$x$y$z$a$b"):
            self.assertFalse(hasher.verify("motdepasse1", garbage))

    def test_une_empreinte_plus_ancienne_reste_verifiable_apres_durcissement(self):
        old = ScryptPasswordHasher(n=2 ** 12).hash("motdepasse1")
        self.assertTrue(ScryptPasswordHasher(n=2 ** 15).verify("motdepasse1", old))


class SqlModelAuthTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "comptes.db")
        self.db = AuthDatabase(self.path)
        self.accounts, self.tokens = SqlModelAccountRepository(self.db), SqlModelRememberTokens(self.db)

    def test_comptes(self):
        saved = self.accounts.add(account())
        self.assertEqual((saved.id, self.accounts.count()), (1, 1))
        self.assertEqual(self.accounts.by_email("rina@exemple.fr"), saved)
        self.assertEqual(self.accounts.by_id(1), saved)
        self.assertIsNone(self.accounts.by_email("autre@exemple.fr"))
        self.assertIsNone(self.accounts.by_id(99))

    def test_email_unique(self):
        self.accounts.add(account())
        with self.assertRaises(DomainError):
            self.accounts.add(account(name="Doublon"))

    def test_mise_a_jour(self):
        import dataclasses
        saved = self.accounts.add(account())
        self.accounts.update(dataclasses.replace(saved, password_hash="nouveau", name="Rina L."))
        again = self.accounts.by_id(saved.id)
        self.assertEqual((again.password_hash, again.name), ("nouveau", "Rina L."))

    def test_les_donnees_survivent_a_la_fermeture(self):
        self.accounts.add(account())
        reopened = SqlModelAccountRepository(AuthDatabase(self.path))
        self.assertEqual(reopened.by_email("rina@exemple.fr").name, "Rina")

    def test_jetons(self):
        saved = self.accounts.add(account())
        token = self.tokens.issue(saved.id, NOW + dt.timedelta(days=30))
        self.assertEqual(self.tokens.resolve(token, NOW), saved.id)
        self.assertIsNone(self.tokens.resolve("inconnu", NOW))
        self.assertIsNone(self.tokens.resolve(token, NOW + dt.timedelta(days=31)))   # expiré
        again = self.tokens.issue(saved.id, NOW + dt.timedelta(days=30))
        self.tokens.revoke(again)
        self.assertIsNone(self.tokens.resolve(again, NOW))
        t1, t2 = (self.tokens.issue(saved.id, NOW + dt.timedelta(days=1)) for _ in range(2))
        self.tokens.revoke_all(saved.id)
        self.assertEqual([self.tokens.resolve(t, NOW) for t in (t1, t2)], [None, None])

    def test_le_jeton_n_est_jamais_stocke_en_clair(self):
        saved = self.accounts.add(account())
        token = self.tokens.issue(saved.id, NOW + dt.timedelta(days=30))
        with sqlite3.connect(self.path) as con:
            stored = [row[0] for row in con.execute("SELECT token_hash FROM remember_tokens")]
        self.assertEqual(len(stored), 1)
        self.assertNotEqual(stored[0], token)
        with open(self.path, "rb") as f:
            self.assertNotIn(token.encode(), f.read())


class LocalSessionTest(unittest.TestCase):
    def test_aller_retour_et_fichier_illisible(self):
        path = os.path.join(tempfile.mkdtemp(), "session.json")
        store = JsonFileLocalSessionStore(path)
        self.assertEqual(store.load(), LocalSession())                  # fichier absent
        store.save(LocalSession("jeton", "rina@exemple.fr", "Rina"))
        self.assertEqual(store.load(), LocalSession("jeton", "rina@exemple.fr", "Rina"))
        with open(path, "w") as f:
            f.write("{pas du json")
        self.assertEqual(store.load(), LocalSession())                  # on repart de zéro, sans planter

    @unittest.skipIf(sys.platform.startswith("win"), "droits POSIX")
    def test_fichier_reserve_au_proprietaire(self):
        path = os.path.join(tempfile.mkdtemp(), "session.json")
        JsonFileLocalSessionStore(path).save(LocalSession("jeton"))
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)


class WiringTest(unittest.TestCase):
    def test_lot_complet(self):
        folder = tempfile.mkdtemp()
        ports = sqlmodel_auth_ports(folder)
        self.assertEqual(sorted(os.listdir(folder)), ["comptes.db"])    # la base des comptes est séparée des données


if __name__ == "__main__":
    unittest.main()
