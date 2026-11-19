"""Écran d'authentification en deux volets : présentation à gauche, formulaire à droite.

Trois formulaires sur la même mise en page : connexion, création de compte, mot de passe oublié.
"""
from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from ..contract.dto import AuthForm, AuthMode
from ..contract.interfaces import AuthListener, AuthView
from . import theme as t
from .widgets import button, call

LEFT_PANEL = "#E8F2EC"   # vert très pâle de la maquette
FORM_WIDTH = 400

_BENEFITS = ("Rassembler les dépenses de la semaine", "Saisir sans repartir de zéro",
             "Vérifier, puis enregistrer sereinement")

# mode : (titre, sous-titre, bouton principal, champs à afficher)
_FORMS = {
    AuthMode.LOGIN: ("Bon retour.", "Connectez-vous pour retrouver votre espace personnel.", "→   Se connecter",
                     ("email", "password")),
    AuthMode.REGISTER: ("Créez votre espace.", "Quelques instants suffisent pour commencer à noter vos dépenses.",
                        "Créer mon compte", ("name", "email", "password", "confirmation")),
    AuthMode.RESET: ("Mot de passe oublié ?", "Saisissez la clé de récupération remise à la création de votre "
                     "compte pour choisir un nouveau mot de passe.", "Modifier le mot de passe",
                     ("email", "recovery_key", "new_password")),
}
_CAPTIONS = {"name": "Nom affiché", "email": "Adresse e-mail", "password": "Mot de passe",
             "confirmation": "Confirmer le mot de passe", "recovery_key": "Clé de récupération",
             "new_password": "Nouveau mot de passe"}


def _text(parent, text, size=13, weight="normal", color=t.TEXT, **options):
    return ctk.CTkLabel(parent, text=text, font=t.font(size, weight), text_color=color, anchor="w",
                        justify="left", **options)


def _link(parent, text, command, color=t.GREEN, size=12, bold=True):
    return ctk.CTkButton(parent, text=text, command=command, width=0, height=22, fg_color="transparent",
                         hover_color=t.WHITE, text_color=color, font=t.font(size, "bold" if bold else "normal"),
                         corner_radius=4)


class CtkAuthView(AuthView):
    def __init__(self, parent):
        self._listener: Optional[AuthListener] = None
        self._mode = AuthMode.LOGIN
        self._name, self._email = ctk.StringVar(), ctk.StringVar()
        self._password, self._confirmation = ctk.StringVar(), ctk.StringVar()
        self._recovery = ctk.StringVar()
        self._remember = ctk.BooleanVar(value=False)
        self._error = None

        parent.grid_columnconfigure(0, weight=2, uniform="auth")
        parent.grid_columnconfigure(1, weight=3, uniform="auth")
        parent.grid_rowconfigure(0, weight=1)
        self._build_presentation(parent)
        right = ctk.CTkFrame(parent, fg_color=t.WHITE, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        self._form = ctk.CTkFrame(right, fg_color=t.WHITE, corner_radius=0)
        self._form.place(relx=0.5, rely=0.5, anchor="center")

    # ---- volet gauche (présentation) ---------------------------------------------------------------
    def _build_presentation(self, parent) -> None:
        left = ctk.CTkFrame(parent, fg_color=LEFT_PANEL, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        _text(left, "▥   Repère", 22, "normal", t.GREEN).pack(anchor="w", padx=48, pady=(40, 0))
        _text(left, "Un outil simple. Des calculs transparents. Vous gardez la main.", 12, "normal",
              t.GREEN).pack(side="bottom", anchor="w", padx=48, pady=(0, 36))
        middle = ctk.CTkFrame(left, fg_color="transparent")
        middle.pack(expand=True, fill="x", padx=48)
        _text(middle, "VOTRE RENDEZ-VOUS AVEC VOS COMPTES", 11, "bold", t.GREEN).pack(anchor="w")
        _text(middle, "L'esprit tranquille,\nligne après ligne.", 36, "normal", t.GREEN).pack(
            anchor="w", pady=(14, 14))
        _text(middle, "Notez vos dépenses, vérifiez votre solde et retrouvez des comptes qui vous "
                      "ressemblent.", 14, "normal", t.GREEN, wraplength=380).pack(anchor="w", pady=(0, 26))
        card = ctk.CTkFrame(middle, fg_color=t.WHITE, corner_radius=12)
        card.pack(fill="x")
        for i, benefit in enumerate(_BENEFITS):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=(20 if i == 0 else 8, 20 if i == len(_BENEFITS) - 1 else 8))
            _text(row, "✓", 13, "bold", t.GREEN).pack(side="left", padx=(0, 14))
            _text(row, benefit, 13).pack(side="left")

    # ---- volet droit (formulaire) ------------------------------------------------------------------------
    def set_listener(self, listener: AuthListener) -> None:
        self._listener = listener

    def _get(self):
        return self._listener

    def _submit(self) -> None:
        call(self._get, "on_submit")

    def show_mode(self, mode: AuthMode, greeting: str, email: str = "") -> None:
        self._mode = mode
        for var in (self._name, self._password, self._confirmation, self._recovery):
            var.set("")
        self._email.set(email)
        for child in self._form.winfo_children():
            child.destroy()
        title, subtitle, submit_text, fields = _FORMS[mode]
        f = self._form
        _text(f, greeting, 11, "bold", t.GREEN).pack(anchor="w")
        _text(f, title, 30, "bold").pack(anchor="w", pady=(10, 6))
        _text(f, subtitle, 13, "normal", t.MUTED, wraplength=FORM_WIDTH).pack(anchor="w", pady=(0, 24))

        first = None
        for key in fields:
            entry = self._add_field(f, key)
            first = first or entry
        if mode is AuthMode.LOGIN:
            options = ctk.CTkFrame(f, fg_color="transparent", width=FORM_WIDTH)
            options.pack(fill="x", pady=(2, 0))
            ctk.CTkCheckBox(options, text="Rester connecté·e", variable=self._remember, fg_color=t.GREEN,
                            hover_color=t.GREEN_HOVER, border_color=t.BORDER, checkmark_color=t.WHITE,
                            text_color=t.TEXT, font=t.font(12), checkbox_width=18, checkbox_height=18,
                            corner_radius=4, border_width=2).pack(side="left")
            _link(options, "Mot de passe oublié ?",
                  lambda: call(self._get, "on_switch_mode", AuthMode.RESET)).pack(side="right")

        self._error = _text(f, "", 12, "normal", t.RED, wraplength=FORM_WIDTH)
        self._error.pack(anchor="w", pady=(10, 0))
        submit = button(f, submit_text, self._submit, "primary", 190)
        submit.configure(height=44)
        submit.pack(anchor="w", pady=(12, 0))

        ctk.CTkFrame(f, height=1, fg_color=t.BORDER, width=FORM_WIDTH, corner_radius=0).pack(fill="x", pady=22)
        if mode is AuthMode.LOGIN:
            _text(f, "Vos données financières restent privées. Aucun solde n'est affiché avant votre "
                     "connexion.", 11, "normal", t.MUTED, wraplength=FORM_WIDTH).pack(anchor="w")
            switch = ctk.CTkFrame(f, fg_color="transparent")
            switch.pack(fill="x", pady=(14, 0))
            _text(switch, "Pas encore de compte ?", 12, "normal", t.MUTED).pack(side="left")
            _link(switch, "Créer un compte", lambda: call(self._get, "on_switch_mode", AuthMode.REGISTER)).pack(
                side="left", padx=(4, 0))
        else:
            _link(f, "←  Retour à la connexion", lambda: call(self._get, "on_switch_mode", AuthMode.LOGIN)).pack(
                anchor="w")
        links = ctk.CTkFrame(f, fg_color="transparent")
        links.pack(fill="x", pady=(14, 0))
        _link(links, "Confidentialité", lambda: call(self._get, "on_privacy"), t.MUTED, 11, False).pack(side="left")
        _link(links, "Besoin d'aide ?", lambda: call(self._get, "on_help"), t.MUTED, 11, False).pack(
            side="left", padx=(14, 0))
        if first is not None:
            self._form.after(120, first.focus_set)

    def _add_field(self, parent, key: str):
        variable = {"name": self._name, "email": self._email, "password": self._password,
                    "confirmation": self._confirmation, "recovery_key": self._recovery,
                    "new_password": self._password}[key]
        secret = key in ("password", "confirmation", "new_password")
        _text(parent, _CAPTIONS[key], 12, "bold").pack(anchor="w", pady=(0, 6))
        holder = ctk.CTkFrame(parent, fg_color="transparent", width=FORM_WIDTH, height=44)
        holder.pack(fill="x", pady=(0, 16))
        holder.pack_propagate(False)
        entry = ctk.CTkEntry(holder, textvariable=variable, height=44, corner_radius=8, border_width=1,
                             border_color=t.BORDER, fg_color=t.WHITE, text_color=t.TEXT, font=t.font(13),
                             show="•" if secret else "")
        entry.pack(fill="both", expand=True)
        entry.bind("<Return>", lambda _e: self._submit())
        if secret:
            self._add_visibility_toggle(holder, entry)
        elif key == "email":
            _text(holder, "✉", 15, "normal", t.MUTED).place(relx=1.0, x=-14, rely=0.5, anchor="e")
        return entry

    @staticmethod
    def _add_visibility_toggle(holder, entry) -> None:
        state = {"visible": False}
        toggle = ctk.CTkButton(holder, text="Afficher", width=64, height=28, fg_color=t.WHITE,
                               hover_color=t.GREEN_LIGHT, text_color=t.GREEN, font=t.font(11, "bold"),
                               corner_radius=6)

        def flip() -> None:
            state["visible"] = not state["visible"]
            entry.configure(show="" if state["visible"] else "•")
            toggle.configure(text="Masquer" if state["visible"] else "Afficher")

        toggle.configure(command=flip)
        toggle.place(relx=1.0, x=-8, rely=0.5, anchor="e")

    def get_form(self) -> AuthForm:
        return AuthForm(self._name.get(), self._email.get(), self._password.get(), self._confirmation.get(),
                        self._recovery.get(), bool(self._remember.get()))

    def show_error(self, message: str) -> None:
        if self._error is not None:
            self._error.configure(text=message)

    def clear_secrets(self) -> None:
        for var in (self._password, self._confirmation, self._recovery):
            var.set("")
