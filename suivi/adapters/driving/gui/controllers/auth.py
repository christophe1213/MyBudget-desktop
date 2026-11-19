from __future__ import annotations

import datetime as dt
from typing import Callable

from .....application.dto import UserInfo
from .....application.errors import StorageError
from .....application.ports.inbound import Authenticate
from .....domain.model.errors import DomainError
from ..contract.dto import AuthMode
from ..contract.interfaces import AccountListener, AccountView, AuthListener, AuthView, Dialogs, Screens

_PRIVACY = ("Vos comptes et vos transactions restent sur cet ordinateur : rien n'est envoyé sur Internet.\n\n"
            "Les mots de passe ne sont jamais conservés, seulement une empreinte irréversible.")
_HELP = ("• Premier lancement : créez votre compte.\n"
         "• Mot de passe oublié : utilisez la clé de récupération remise à la création du compte.\n"
         "• Trop de tentatives : patientez 5 minutes avant de réessayer.")


class AuthController(AuthListener, AccountListener):
    """Écran d'authentification (connexion, création de compte, réinitialisation) et déconnexion.

    Parle à l'application uniquement par le port entrant `Authenticate` ; les erreurs (identifiants
    incorrects, règle non respectée, stockage) s'affichent sous le formulaire, sans boîte de dialogue.
    """

    def __init__(self, dialogs: Dialogs, view: AuthView, account_view: AccountView, auth: Authenticate,
                 screens: Screens, on_login: Callable[[UserInfo], None],
                 hour: Callable[[], int] = lambda: dt.datetime.now().hour):
        self._dialogs, self._view, self._account = dialogs, view, account_view
        self._auth, self._screens, self._on_login, self._hour = auth, screens, on_login, hour
        self._mode = AuthMode.LOGIN
        view.set_listener(self)
        account_view.set_listener(self)

    # ---- démarrage -------------------------------------------------------------------------------
    def start(self) -> None:
        try:
            user = self._auth.resume()   # « Rester connecté » : on entre directement
        except (DomainError, StorageError):
            user = None
        if user is not None:
            self._enter(user)
            return
        try:
            first_run = not self._auth.has_accounts()
        except StorageError:
            first_run = False
        self._show_mode(AuthMode.REGISTER if first_run else AuthMode.LOGIN)
        self._screens.show_login()

    # ---- actions de l'utilisateur ---------------------------------------------------------------------
    def on_switch_mode(self, mode: AuthMode) -> None:
        self._show_mode(mode)

    def on_submit(self) -> None:
        form = self._view.get_form()
        try:
            if self._mode is AuthMode.LOGIN:
                user = self._auth.login(form.email, form.password, form.remember)
            elif self._mode is AuthMode.REGISTER:
                registration = self._auth.register(form.name, form.email, form.password, form.confirmation)
                self._dialogs.info("Conservez votre clé de récupération",
                                   "Cette clé permet de retrouver l'accès si vous oubliez votre mot de passe. "
                                   "Notez-la en lieu sûr : elle ne sera plus affichée.\n\n"
                                   f"{registration.recovery_key}")
                user = registration.user
            else:
                new_key = self._auth.reset_password(form.email, form.recovery_key, form.password)
                self._dialogs.info("Mot de passe modifié",
                                   "Votre mot de passe a été modifié. Voici votre NOUVELLE clé de récupération "
                                   f"(l'ancienne n'est plus valable) :\n\n{new_key}")
                self._show_mode(AuthMode.LOGIN, form.email)
                return
        except (DomainError, StorageError) as e:
            self._view.clear_secrets()
            self._view.show_error(str(e))
            return
        self._enter(user)

    def on_logout(self) -> None:
        try:
            self._auth.logout()
        except StorageError as e:
            self._dialogs.error("Déconnexion", str(e))
        self._show_mode(AuthMode.LOGIN)
        self._screens.show_login()

    def on_privacy(self) -> None:
        self._dialogs.info("Confidentialité", _PRIVACY)

    def on_help(self) -> None:
        self._dialogs.info("Besoin d'aide ?", _HELP)

    # ---- interne ------------------------------------------------------------------------------------------
    def _enter(self, user: UserInfo) -> None:
        self._account.show_user(user.name, user.email)
        self._screens.show_app()
        self._on_login(user)

    def _show_mode(self, mode: AuthMode, email: str | None = None) -> None:
        self._mode = mode
        if email is None:
            email = (self._auth.last_known_email() or "") if mode is AuthMode.LOGIN else ""
        self._view.show_mode(mode, self._greeting(mode), email)

    def _greeting(self, mode: AuthMode) -> str:
        if mode is AuthMode.REGISTER:
            return "NOUVEAU COMPTE"
        if mode is AuthMode.RESET:
            return "MOT DE PASSE OUBLIÉ"
        name = self._auth.last_known_name()
        if not name:
            return "CONNEXION"
        return f"{'BONJOUR' if self._hour() < 18 else 'BONSOIR'}, {name.split()[0].upper()}"
