"""AuthController avec des vues simulées : écran de connexion, création de compte, réinitialisation."""
import unittest
from unittest.mock import MagicMock

from suivi.adapters.driving.gui.contract import interfaces as v
from suivi.adapters.driving.gui.contract.dto import AuthForm, AuthMode
from suivi.adapters.driving.gui.controllers.auth import AuthController
from suivi.application.use_cases.auth import AuthService

from .fakes import FixedClock, make_auth_ports


class AuthControllerTest(unittest.TestCase):
    def setUp(self, hour=20):
        self.ports = make_auth_ports()
        p = self.ports
        self.auth = AuthService(p.accounts, p.hasher, p.tokens, p.local, FixedClock())
        self.view, self.account = MagicMock(spec=v.AuthView), MagicMock(spec=v.AccountView)
        self.screens, self.dialogs = MagicMock(spec=v.Screens), MagicMock(spec=v.Dialogs)
        self.entered = []
        self.hour = hour
        self.controller = self.make_controller()

    def make_controller(self, auth=None):
        return AuthController(self.dialogs, self.view, self.account, auth or self.auth, self.screens,
                              self.entered.append, hour=lambda: self.hour)

    def fill(self, **fields):
        self.view.get_form.return_value = AuthForm(**fields)

    def create_account(self):
        self.auth.register("Rina Laurent", "rina@exemple.fr", "motdepasse1", "motdepasse1")
        self.auth.logout()

    def test_premier_lancement_propose_de_creer_le_compte(self):
        self.controller.start()
        self.view.show_mode.assert_called_with(AuthMode.REGISTER, "NOUVEAU COMPTE", "")
        self.screens.show_login.assert_called_once()
        self.assertEqual(self.entered, [])

    def test_creation_de_compte_affiche_la_cle_de_recuperation_puis_entre(self):
        self.controller.start()
        self.fill(name="Rina Laurent", email="rina@exemple.fr", password="motdepasse1", confirmation="motdepasse1")
        self.controller.on_submit()
        title, message = self.dialogs.info.call_args[0]
        self.assertIn("clé de récupération", title.lower())
        self.assertRegex(message, r"[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}")
        self.account.show_user.assert_called_with("Rina Laurent", "rina@exemple.fr")
        self.screens.show_app.assert_called_once()
        self.assertEqual(len(self.entered), 1)

    def test_salutation_selon_l_heure_et_email_prerempli(self):
        self.create_account()
        self.controller.start()
        self.view.show_mode.assert_called_with(AuthMode.LOGIN, "BONSOIR, RINA", "rina@exemple.fr")
        self.hour = 9
        self.controller.on_switch_mode(AuthMode.LOGIN)
        self.assertEqual(self.view.show_mode.call_args[0][1], "BONJOUR, RINA")

    def test_connexion_reussie(self):
        self.create_account()
        self.controller.start()
        self.fill(email="rina@exemple.fr", password="motdepasse1", remember=True)
        self.controller.on_submit()
        self.screens.show_app.assert_called_once()
        self.assertEqual(self.entered[0].name, "Rina Laurent")
        self.assertIsNotNone(self.ports.local.session.token)             # « Rester connecté » coché

    def test_mauvais_mot_de_passe_affiche_l_erreur_sous_le_formulaire(self):
        self.create_account()
        self.controller.start()
        self.fill(email="rina@exemple.fr", password="mauvais123")
        self.controller.on_submit()
        self.view.show_error.assert_called_with("E-mail ou mot de passe incorrect.")
        self.view.clear_secrets.assert_called_once()
        self.screens.show_app.assert_not_called()
        self.dialogs.warning.assert_not_called()                         # pas de boîte de dialogue : erreur en ligne

    def test_reprise_automatique_de_la_session(self):
        self.create_account()
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=True)
        p = self.ports
        relaunched = AuthService(p.accounts, p.hasher, p.tokens, p.local, FixedClock())
        self.make_controller(relaunched).start()
        self.screens.show_app.assert_called_once()                       # pas d'écran de connexion
        self.screens.show_login.assert_not_called()
        self.assertEqual(len(self.entered), 1)

    def test_deconnexion_revient_a_l_ecran_de_connexion(self):
        self.create_account()
        self.auth.login("rina@exemple.fr", "motdepasse1", remember=True)
        self.controller.on_logout()
        self.assertIsNone(self.auth.current_user())
        self.assertIsNone(self.ports.local.session.token)
        self.screens.show_login.assert_called_once()
        self.assertEqual(self.view.show_mode.call_args[0][0], AuthMode.LOGIN)

    def test_mot_de_passe_oublie(self):
        self.auth_key = self.auth.register("Rina", "rina@exemple.fr", "motdepasse1", "motdepasse1").recovery_key
        self.auth.logout()
        self.controller.on_switch_mode(AuthMode.RESET)
        self.fill(email="rina@exemple.fr", recovery_key=self.auth_key, password="nouveaumdp9")
        self.controller.on_submit()
        self.assertIn("NOUVELLE clé", self.dialogs.info.call_args[0][1])
        self.view.show_mode.assert_called_with(AuthMode.LOGIN, "BONSOIR, RINA", "rina@exemple.fr")
        self.assertEqual(self.auth.login("rina@exemple.fr", "nouveaumdp9", False).name, "Rina")

    def test_pages_d_information(self):
        self.controller.on_privacy()
        self.controller.on_help()
        self.assertEqual([c[0][0] for c in self.dialogs.info.call_args_list], ["Confidentialité", "Besoin d'aide ?"])


if __name__ == "__main__":
    unittest.main()
