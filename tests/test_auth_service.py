"""Le cas d'usage d'authentification et les règles de compte, avec des adaptateurs en mémoire."""
import unittest

from suivi.application.use_cases.auth import LOCK_MINUTES, MAX_FAILURES, REMEMBER_DAYS, AuthService
from suivi.domain.model.account import check_display_name, check_password, normalize_email, normalize_recovery_key
from suivi.domain.model.errors import AuthenticationError, DomainError

from .fakes import FixedClock, make_auth_ports


class AccountRulesTest(unittest.TestCase):
    def test_email(self):
        self.assertEqual(normalize_email("  Rina.Laurent@Exemple.FR "), "rina.laurent@exemple.fr")
        for bad in ("", "rina", "rina@", "rina@exemple", "a b@c.fr"):
            with self.assertRaises(DomainError):
                normalize_email(bad)

    def test_mot_de_passe(self):
        check_password("motdepasse1", "rina@exemple.fr")
        for bad in ("court", "aaaaaaaaaa", "rina@exemple.fr"):
            with self.assertRaises(DomainError):
                check_password(bad, "rina@exemple.fr")

    def test_nom_et_cle(self):
        self.assertEqual(check_display_name("  Rina   Laurent "), "Rina Laurent")
        with self.assertRaises(DomainError):
            check_display_name("   ")
        self.assertEqual(normalize_recovery_key("a1b2-c3d4 e5f6"), "A1B2C3D4E5F6")


class AuthServiceTest(unittest.TestCase):
    def setUp(self):
        self.ports, self.clock = make_auth_ports(), FixedClock()
        self.auth = self.new_service()
        self.registration = self.auth.register("Rina Laurent", "Rina@Exemple.fr", "motdepasse1", "motdepasse1")
        self.auth.logout()

    def new_service(self):
        p = self.ports
        return AuthService(p.accounts, p.hasher, p.tokens, p.local, self.clock)

    def test_inscription(self):
        self.assertEqual(self.registration.user.email, "rina@exemple.fr")
        self.assertRegex(self.registration.recovery_key, r"^[0-9A-F]{4}(-[0-9A-F]{4}){3}$")
        stored = self.ports.accounts.by_email("rina@exemple.fr")
        self.assertNotIn("motdepasse1", stored.password_hash)          # jamais le mot de passe en clair
        self.assertTrue(self.auth.has_accounts())

    def test_inscription_refusee(self):
        with self.assertRaisesRegex(DomainError, "ne correspondent pas"):
            self.auth.register("Paul", "paul@exemple.fr", "motdepasse1", "autrechose1")
        with self.assertRaisesRegex(DomainError, "existe déjà"):
            self.auth.register("Autre", "RINA@exemple.fr", "motdepasse1", "motdepasse1")

    def test_connexion_et_message_identique_pour_compte_inconnu_ou_mauvais_mot_de_passe(self):
        self.assertEqual(self.auth.login("rina@exemple.fr", "motdepasse1", False).name, "Rina Laurent")
        messages = set()
        for email, password in (("rina@exemple.fr", "mauvais123"), ("inconnu@exemple.fr", "motdepasse1")):
            with self.assertRaises(AuthenticationError) as caught:
                self.auth.login(email, password, False)
            messages.add(str(caught.exception))
        self.assertEqual(len(messages), 1)                              # on ne révèle pas si le compte existe

    def test_verrouillage_apres_echecs_repetes_puis_deblocage(self):
        for _ in range(MAX_FAILURES):
            with self.assertRaises(AuthenticationError):
                self.auth.login("rina@exemple.fr", "mauvais123", False)
        with self.assertRaisesRegex(AuthenticationError, "Trop de tentatives"):
            self.auth.login("rina@exemple.fr", "motdepasse1", False)    # même le bon mot de passe est refusé
        self.clock.advance(minutes=LOCK_MINUTES, seconds=1)
        self.assertEqual(self.auth.login("rina@exemple.fr", "motdepasse1", False).email, "rina@exemple.fr")

    def test_rester_connecte_reprend_la_session_au_lancement_suivant(self):
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=True)
        self.assertIsNotNone(self.ports.local.session.token)
        relaunched = self.new_service()                                  # nouveau lancement de l'application
        self.assertEqual(relaunched.resume().name, "Rina Laurent")
        self.assertEqual(relaunched.last_known_name(), "Rina Laurent")

    def test_sans_rester_connecte_pas_de_reprise(self):
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=False)
        self.assertIsNone(self.new_service().resume())

    def test_jeton_expire(self):
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=True)
        self.clock.advance(days=REMEMBER_DAYS + 1)
        self.assertIsNone(self.new_service().resume())
        self.assertIsNone(self.ports.local.session.token)               # le jeton périmé est oublié

    def test_deconnexion_revoque_le_jeton(self):
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=True)
        token = self.ports.local.session.token
        self.auth.logout()
        self.assertIsNone(self.auth.current_user())
        self.assertIsNone(self.ports.tokens.resolve(token, self.clock.now()))
        self.assertIsNone(self.new_service().resume())

    def test_reinitialisation_par_cle_de_recuperation(self):
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=True)
        with self.assertRaises(AuthenticationError):
            self.auth.reset_password("rina@exemple.fr", "0000-0000-0000-0000", "nouveaumdp9")
        key = self.registration.recovery_key.lower().replace("-", " ")   # saisie tolérante (casse, séparateurs)
        new_key = self.auth.reset_password("rina@exemple.fr", key, "nouveaumdp9")
        self.assertNotEqual(new_key, self.registration.recovery_key)
        with self.assertRaises(AuthenticationError):
            self.auth.login("rina@exemple.fr", "motdepasse1", False)     # l'ancien mot de passe ne marche plus
        self.assertEqual(self.auth.login("rina@exemple.fr", "nouveaumdp9", False).name, "Rina Laurent")
        with self.assertRaises(AuthenticationError):                     # l'ancienne clé est invalidée
            self.auth.reset_password("rina@exemple.fr", self.registration.recovery_key, "encoreautre1")
        self.assertIsNone(self.new_service().resume())                   # sessions « Rester connecté » révoquées


if __name__ == "__main__":
    unittest.main()
