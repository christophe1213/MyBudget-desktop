"""Page « Transactions » : MAQUETTE (squelette) reprenant les écrans de la version web.

Rien n'est branché : pas de contrôleur, pas de port, pas de données réelles. Les montants et les lignes sont des
exemples fixes. Seule la navigation entre les écrans de la maquette fonctionne (afficher / masquer un cadre), pour
pouvoir parcourir tout le parcours :

    liste ──► choix de l'opération ──► détails (dépense | versement | transfert) ──► récapitulatif ──► liste

La page « Saisie » existante (`transactions_view.py`) n'est pas touchée.

Pour brancher les fonctions plus tard : remplacer les appels à `_todo` par des écouteurs (comme les autres vues :
un contrat dans `contract/interfaces.py`, un contrôleur dans `controllers/`), puis alimenter les tableaux avec de
vraies `Row` à la place des constantes `SAMPLE_*` ci-dessous.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from . import theme as t
from .widgets import Column, Table, button, card, combo, entry, field, label, segmented, tinted

# ---- données d'exemple (à remplacer par les vraies données) ----------------------------------------------------
SAMPLE_WALLETS = ("Tous les portefeuilles", "Mobile money", "Espèces", "Banque")
SAMPLE_BUDGETS = ("Électricité", "Nourriture", "Loyer", "Internet", "Transport")

SAMPLE_HISTORY = (
    Row("h0", ("20/10/2026", "Versement", "4 budget(s)", "Paie d'octobre", "+200 000 Ar")),
    Row("h1", ("18/10/2026", "Dépense", "Nourriture", "Courses", "−45 000 Ar")),
    Row("h2", ("15/10/2026", "Dépense", "Électricité", "Paiement de facture", "−4 000 Ar")),
)
SAMPLE_DETAIL = (
    Row("d0", ("Électricité", "4", "35 000 Ar")),
    Row("d1", ("Nourriture", "4", "22 000 Ar")),
    Row("d2", ("Loyer", "10", "100 000 Ar")),
    Row("d3", ("Budget par défaut", "—", "43 000 Ar")),
)
SAMPLE_PENDING = (
    Row("p0", ("22/10/2026", "Versement", "4 budget(s)", "Réparti via le panier", "+200 000 Ar")),
    Row("p1", ("22/10/2026", "Transfert", "Mobile money → Espèces", "Frais 2 000 Ar (Budget par défaut)",
               "−62 000 Ar")),
)
SAMPLE_BASKET = (
    Row("b0", ("Électricité", "15 000 Ar", "25 000 Ar", "4", "35 000 Ar")),
    Row("b1", ("Nourriture", "8 000 Ar", "10 000 Ar", "4", "22 000 Ar")),
    Row("b2", ("Transport", "5 000 Ar", "30 000 Ar", "4", "0 Ar")),
)
SAMPLE_TRANSFER_BASKET = (
    Row("t0", ("Nourriture", "Nourriture", "10 000 Ar", "4", "10 000 Ar")),
    Row("t1", ("Transport", "Transport", "30 000 Ar", "4", "20 000 Ar")),
)

_HISTORY_COLUMNS = (Column("date", "Date", 110), Column("type", "Type", 110), Column("budget", "Budget", 210),
                    Column("label", "Libellé", 280), Column("amount", "Montant", 130, "e"))
_STEPS = ("1  Opération", "2  Détails", "3  Récapitulatif")


# ---- petits composants de la maquette ---------------------------------------------------------------------------
def _pill(parent, text: str, fg: str = t.GREEN_LIGHT, color: str = t.GREEN, width: int = 96) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=t.font(12, "bold"), text_color=color, fg_color=fg,
                        corner_radius=10, width=width, height=24)


def _screen_header(parent, title: str, subtitle: str, action: Optional[tuple[str, Callable[[], None], str]] = None):
    """Titre + sous-titre à gauche, bouton d'action facultatif à droite : (texte, commande, style)."""
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    bar.pack(fill="x", pady=(0, 14))
    texts = ctk.CTkFrame(bar, fg_color="transparent")
    texts.pack(side="left")
    label(texts, title, "heading").pack(anchor="w")
    label(texts, subtitle, "muted").pack(anchor="w")
    if action is not None:
        text, command, kind = action
        button(bar, text, command, kind, 200).pack(side="right")
    return bar


def _stepper(parent, active: int) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=(0, 14))
    for number, text in enumerate(_STEPS, start=1):
        on = number == active
        ctk.CTkLabel(row, text=text, font=t.font(12, "bold" if on else "normal"), corner_radius=12, width=130,
                     height=24, fg_color=t.GREEN if on else t.SURFACE,
                     text_color=t.WHITE if on else t.MUTED).pack(side="left", padx=(0, 8))


def _kpi(parent, caption: str, value: str, color: str = t.TEXT) -> ctk.CTkFrame:
    box = card(parent)
    label(box, caption, "muted").pack(anchor="w", padx=16, pady=(12, 0))
    ctk.CTkLabel(box, text=value, font=t.font(22, "bold"), text_color=color, anchor="w").pack(
        anchor="w", padx=16, pady=(0, 12))
    return box


def _banner(parent, text: str, action_text: Optional[str] = None,
            action: Optional[Callable[[], None]] = None) -> None:
    box = tinted(parent, t.AMBER_LIGHT)
    box.pack(fill="x", pady=(0, 14))
    label(box, text, "strong", color=t.AMBER_DARK).pack(side="left", padx=16, pady=10)
    if action_text and action:
        button(box, action_text, action, "secondary", 120).pack(side="right", padx=12, pady=8)


def _notice(parent, text: str, fg: str, color: str) -> ctk.CTkFrame:
    """Bandeau d'information (écart, reste à répartir…)."""
    box = tinted(parent, fg)
    box.pack(fill="x", padx=20, pady=(0, 14))
    label(box, text, "strong", color=color, wraplength=640).pack(anchor="w", padx=14, pady=10)
    return box


def _inputs(parent, *specs: tuple[str, str, Optional[Sequence[str]]]) -> list:
    """Une ligne de champs « légende au-dessus » : (légende, valeur, choix) ; avec des choix = liste déroulante."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=(0, 14))
    variables = []
    for column, (caption, value, choices) in enumerate(specs):
        row.grid_columnconfigure(column, weight=1, uniform="inputs")
        holder = field(row, caption)
        holder.grid(row=0, column=column, sticky="ew", padx=(0, 14) if column < len(specs) - 1 else 0)
        variable = ctk.StringVar(value=value)
        widget = combo(holder, variable, 10, values=choices) if choices else entry(holder, variable, 10)
        widget.pack(fill="x")
        variables.append(variable)
    return variables


def _table(parent, columns: Sequence[Column], rows: Sequence[Row], height: int) -> Table:
    table = Table(parent, columns, height=height)
    table.show(rows)
    return table


class CtkTransactionsPageView:
    """Maquette de la page « Transactions » (ne dépend d'aucun contrat : rien n'est encore branché)."""

    def __init__(self, parent):
        self.current = ""
        self._screens: dict[str, ctk.CTkFrame] = {}
        self._build_wallet_bar(parent)
        container = ctk.CTkScrollableFrame(parent, fg_color=t.WHITE, corner_radius=0)
        container.pack(fill="both", expand=True)
        for name, build in (("list", self._build_list), ("choice", self._build_choice),
                            ("expense", self._build_expense), ("deposit", self._build_deposit),
                            ("transfer", self._build_transfer), ("review", self._build_review)):
            screen = ctk.CTkFrame(container, fg_color=t.WHITE, corner_radius=0)
            self._screens[name] = screen
            build(screen)
        self._show("list")

    # ---- navigation de la maquette (affichage seulement) --------------------------------------------------------
    def _show(self, name: str) -> None:
        for screen in self._screens.values():
            screen.pack_forget()
        self._screens[name].pack(fill="x", anchor="n")
        self.current = name

    def _go(self, name: str) -> Callable[[], None]:
        return lambda: self._show(name)

    def _todo(self) -> None:
        """Emplacement d'une future fonction : volontairement vide dans la maquette."""

    # ---- barre du portefeuille (commune à tous les écrans) -------------------------------------------------------
    def _build_wallet_bar(self, parent) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        holder = field(bar, "Portefeuille")
        holder.pack(side="left")
        self._wallet = ctk.StringVar(value="Mobile money")
        combo(holder, self._wallet, 260, values=SAMPLE_WALLETS).pack()    # TODO(fonction) : changer de portefeuille
        _pill(bar, "Numérique").pack(side="left", padx=(14, 0), pady=(20, 0))
        label(bar, "Solde : 151 000 Ar", "strong").pack(side="left", padx=(12, 0), pady=(20, 0))
        label(bar, "Maquette · données d'exemple", "muted").pack(side="right", pady=(20, 0))
        ctk.CTkFrame(parent, height=1, fg_color=t.BORDER, corner_radius=0).pack(fill="x", pady=(0, 14))

    # ---- écran 1 : liste des transactions --------------------------------------------------------------------------
    def _build_list(self, screen) -> None:
        _screen_header(screen, "Transactions", "Portefeuille : Mobile money",
                       ("+ Nouvelle transaction", self._go("choice"), "primary"))
        kpis = ctk.CTkFrame(screen, fg_color="transparent")
        kpis.pack(fill="x", pady=(0, 14))
        for column, (caption, value, color) in enumerate((("Solde actuel", "151 000 Ar", t.TEXT),
                                                          ("Entrées (octobre)", "+200 000 Ar", t.GREEN),
                                                          ("Sorties (octobre)", "−49 000 Ar", t.RED))):
            kpis.grid_columnconfigure(column, weight=1, uniform="kpi")
            _kpi(kpis, caption, value, color).grid(row=0, column=column, sticky="ew",
                                                   padx=(0, 12) if column < 2 else 0)
        _banner(screen, "Brouillon en cours · 2 transaction(s)", "Reprendre", self._go("review"))
        _table(screen, _HISTORY_COLUMNS, SAMPLE_HISTORY, 6)
        label(screen, "Sélectionnez une ligne pour afficher le détail de l'opération.", "muted").pack(
            anchor="w", pady=(8, 10))
        detail = card(screen)
        detail.pack(fill="x")
        label(detail, "Détail : Versement du 20/10/2026 · Paie d'octobre", "section").pack(
            anchor="w", padx=16, pady=(12, 8))
        inner = ctk.CTkFrame(detail, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 12))
        _table(inner, (Column("budget", "Budget", 300), Column("days", "Jours", 100, "e"),
                       Column("amount", "Montant", 160, "e")), SAMPLE_DETAIL, 4)

    # ---- écran 2 : choix de l'opération ------------------------------------------------------------------------------
    def _build_choice(self, screen) -> None:
        _screen_header(screen, "Nouvelle transaction", "Choisissez l'opération",
                       ("Annuler", self._go("list"), "secondary"))
        _stepper(screen, 1)
        row = ctk.CTkFrame(screen, fg_color="transparent")
        row.pack(fill="x")
        for column, (glyph, title, text, target) in enumerate((
                ("−", "Dépense", "Une facture, un achat", "expense"),
                ("+", "Versement", "Salaire ou rentrée, réparti dans les budgets", "deposit"),
                ("⇄", "Transfert", "Vers un autre portefeuille, avec frais", "transfer"))):
            row.grid_columnconfigure(column, weight=1, uniform="ops")
            box = card(row)
            box.grid(row=0, column=column, sticky="nsew", padx=(0, 14) if column < 2 else 0)
            ctk.CTkLabel(box, text=glyph, font=t.font(34, "bold"), text_color=t.GREEN, anchor="w").pack(
                anchor="w", padx=20, pady=(18, 0))
            label(box, title, "heading").pack(anchor="w", padx=20)
            label(box, text, "muted", wraplength=210).pack(anchor="w", padx=20, pady=(0, 14))
            button(box, "Choisir", self._go(target), "secondary").pack(fill="x", padx=20, pady=(0, 18))

    # ---- écran 3 : détails d'une dépense ------------------------------------------------------------------------------
    def _build_expense(self, screen) -> None:
        _screen_header(screen, "Dépense", "Étape 2 sur 3")
        _stepper(screen, 2)
        form = card(screen)
        form.pack(fill="x")
        ctk.CTkFrame(form, height=14, fg_color="transparent").pack()
        _inputs(form, ("Date", "22/10/2026", None), ("Montant (Ar)", "", None))
        _inputs(form, ("Catégorie de budget", SAMPLE_BUDGETS[0], SAMPLE_BUDGETS), ("Libellé", "", None))
        self._form_footer(form, "Ajouter à la liste")

    # ---- écran 3 : détails d'un versement (panier de budgets) ------------------------------------------------------
    def _build_deposit(self, screen) -> None:
        _screen_header(screen, "Versement", "Étape 2 sur 3")
        _stepper(screen, 2)
        form = card(screen)
        form.pack(fill="x")
        ctk.CTkFrame(form, height=14, fg_color="transparent").pack()
        _inputs(form, ("Date", "22/10/2026", None), ("Montant versé (Ar)", "200 000", None))
        label(form, "Panier de budgets : ajoutez les budgets à alimenter. Suggestion = coût par jour × jours − solde "
                    "restant, modifiable.", "muted", wraplength=720).pack(anchor="w", padx=20, pady=(0, 8))
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=(0, 10))
        _table(inner, (Column("budget", "Budget", 200), Column("cost", "Coût / jour", 120, "e"),
                       Column("rest", "Reste", 120, "e"), Column("days", "Jours", 80, "e"),
                       Column("pay", "À verser", 130, "e")), SAMPLE_BASKET, 4)
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 12))
        combo(actions, ctk.StringVar(value="Choisir un budget…"), 210, values=SAMPLE_BUDGETS).pack(side="left")
        button(actions, "+ Ajouter", self._todo, "secondary", 110).pack(side="left", padx=(8, 0))
        button(actions, "Ajouter les budgets critiques", self._todo, "secondary", 230).pack(side="left", padx=(8, 0))
        button(actions, "Retirer la ligne", self._todo, "danger", 150).pack(side="left", padx=(8, 0))
        _notice(form, "Reste à répartir : 143 000 Ar (ira dans le budget par défaut)", t.AMBER_LIGHT, t.AMBER_DARK)
        self._form_footer(form, "Ajouter à la liste")

    # ---- écran 3 : détails d'un transfert ------------------------------------------------------------------------------
    def _build_transfer(self, screen) -> None:
        _screen_header(screen, "Transfert", "Étape 2 sur 3 · depuis Mobile money")
        _stepper(screen, 2)
        form = card(screen)
        form.pack(fill="x")
        ctk.CTkFrame(form, height=14, fg_color="transparent").pack()
        _inputs(form, ("Date", "22/10/2026", None), ("Montant à transférer (Ar)", "60 000", None))
        _inputs(form, ("Portefeuille destinataire", "Espèces (Physique)", ("Espèces (Physique)", "Banque (Numérique)")),
                ("Frais (Ar)", "2 000", None))
        _inputs(form, ("Budget qui paie les frais", "Budget par défaut", ("Budget par défaut",) + SAMPLE_BUDGETS))
        choice = tinted(form, t.SURFACE)
        choice.pack(fill="x", padx=20, pady=(0, 14))
        label(choice, "Transférer par budget ?", "strong").pack(anchor="w", padx=14, pady=(10, 0))
        label(choice, "Non : l'argent passe par le budget par défaut de chaque portefeuille.", "muted").pack(
            anchor="w", padx=14)
        self._by_budget = ctk.StringVar(value="Oui, par budget")
        segmented(choice, self._by_budget, ("Non", "Oui, par budget"), 300).pack(    # TODO(fonction) : afficher / masquer le panier
            anchor="w", padx=14, pady=(8, 12))
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=(0, 10))
        _table(inner, (Column("source", "Budget source", 170), Column("target", "Budget destinataire", 170),
                       Column("rest", "Reste", 110, "e"), Column("days", "Jours", 70, "e"),
                       Column("amount", "Montant", 120, "e")), SAMPLE_TRANSFER_BASKET, 3)
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 12))
        combo(actions, ctk.StringVar(value="Choisir un budget source…"), 230, values=SAMPLE_BUDGETS).pack(side="left")
        button(actions, "+ Ajouter", self._todo, "secondary", 110).pack(side="left", padx=(8, 0))
        button(actions, "Retirer la ligne", self._todo, "danger", 150).pack(side="left", padx=(8, 0))
        _notice(form, "Reste : 30 000 Ar (pris sur le budget par défaut)", t.AMBER_LIGHT, t.AMBER_DARK)
        self._form_footer(form, "Ajouter à la liste")

    def _form_footer(self, form, submit_text: str) -> None:
        foot = ctk.CTkFrame(form, fg_color="transparent")
        foot.pack(fill="x", padx=20, pady=(0, 18))
        button(foot, submit_text, self._go("review"), "primary", 190).pack(side="right")
        button(foot, "Retour", self._go("choice"), "secondary", 110).pack(side="right", padx=(0, 10))

    # ---- écran 4 : récapitulatif et vérification du solde ----------------------------------------------------------
    def _build_review(self, screen) -> None:
        _screen_header(screen, "Récapitulatif", "Étape 3 sur 3 · vérifiez avant d'enregistrer")
        _stepper(screen, 3)
        columns = ctk.CTkFrame(screen, fg_color="transparent")
        columns.pack(fill="x")
        columns.grid_columnconfigure(0, weight=1)
        columns.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        head = ctk.CTkFrame(left, fg_color="transparent")
        head.pack(fill="x", pady=(0, 8))
        label(head, "En attente de validation (2)", "heading").pack(side="left")
        button(head, "+ Nouvelle transaction", self._go("choice"), "secondary", 200).pack(side="right")
        _table(left, (Column("date", "Date", 100), Column("type", "Type", 90), Column("budget", "Budget", 160),
                      Column("label", "Libellé", 190), Column("amount", "Montant", 110, "e")),
               SAMPLE_PENDING, 5)
        buttons = ctk.CTkFrame(left, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        button(buttons, "Modifier", self._todo, "secondary", 110).pack(side="left")
        button(buttons, "Supprimer", self._todo, "danger", 110).pack(side="left", padx=(8, 0))
        label(left, "Sélectionnez une ligne pour la modifier, la supprimer ou voir son détail.", "muted").pack(
            anchor="w", pady=(8, 0))

        check = card(columns, fg=t.SURFACE)
        check.grid(row=0, column=1, sticky="n")
        label(check, "Vérification du solde", "heading").pack(anchor="w", padx=16, pady=(14, 6))
        label(check, "Solde calculé (avec la liste)", "muted").pack(anchor="w", padx=16)
        ctk.CTkLabel(check, text="289 000 Ar", font=t.font(20, "bold"), text_color=t.TEXT, anchor="w").pack(
            anchor="w", padx=16, pady=(0, 10))
        label(check, "Solde réel (argent compté)", "muted").pack(anchor="w", padx=16, pady=(0, 4))
        self._real = ctk.StringVar(value="284 000")                      # TODO(fonction) : calcul de l'écart
        entry(check, self._real, 280).pack(padx=16)
        box = tinted(check, t.RED_LIGHT)
        box.pack(fill="x", padx=16, pady=12)
        label(box, "⚠ Écart de −5 000 Ar", "strong", color=t.RED).pack(anchor="w", padx=12, pady=8)
        button(check, "Enregistrer en brouillon", self._go("list"), "secondary").pack(fill="x", padx=16)
        button(check, "Valider et enregistrer", self._go("list"), "primary").pack(fill="x", padx=16, pady=(8, 14))

        label(check, "Si le solde ne concorde pas : que faire de l'écart ?", "muted", wraplength=280).pack(
            anchor="w", padx=16)
        button(check, "Ajouter une transaction oubliée", self._go("choice"), "secondary").pack(
            fill="x", padx=16, pady=(6, 0))
        button(check, "Créer un ajustement", self._todo, "secondary").pack(fill="x", padx=16, pady=(6, 0))
        button(check, "Valider quand même", self._go("list"), "secondary").pack(fill="x", padx=16, pady=(6, 16))
