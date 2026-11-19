"""Objets échangés entre contrôleurs et vues (aucune dépendance à une bibliothèque graphique)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ALL = "Toutes"  # valeur « pas de filtre » des listes déroulantes


class Tab(Enum):
    DASHBOARD = 0
    ENTRY = 1
    BALANCES = 2
    CATEGORY_DETAILS = 3
    CATEGORIES = 4
    REPORT = 5
    BUDGET = 6
    ANALYSIS = 7
    WALLETS = 8


@dataclass(frozen=True)
class Row:
    """Une ligne de tableau, déjà mise en forme (texte). `emphasis` = ligne de total."""
    id: str
    values: tuple
    emphasis: bool = False


@dataclass(frozen=True)
class TransactionForm:
    date: str
    category: str
    kind: str
    label: str
    amount: str


@dataclass(frozen=True)
class ChartData:
    """Dépenses journalières à tracer : barres + ligne de moyenne + bande d'écart-type + budget retenu."""
    labels: list          # une étiquette de date par jour (ex. '05/09')
    values: list          # dépense de chaque jour
    mean: float
    std: float
    retained: int | None  # budget retenu par l'utilisateur (ligne en pointillés)
    mean_text: str
    retained_text: str | None


class AuthMode(Enum):
    LOGIN = "login"
    REGISTER = "register"
    RESET = "reset"          # mot de passe oublié : réinitialisation par clé de récupération


@dataclass(frozen=True)
class AuthForm:
    """Tout ce que l'utilisateur a saisi sur l'écran d'authentification (texte brut)."""
    name: str = ""
    email: str = ""
    password: str = ""
    confirmation: str = ""
    recovery_key: str = ""
    remember: bool = False


@dataclass(frozen=True)
class PieSlice:
    label: str
    value: float          # taille de la part (seules les proportions comptent)
    amount_text: str      # ex. « 30 000 Ar »
    percent_text: str     # ex. « 33,3 % »


@dataclass(frozen=True)
class PieData:
    slices: tuple[PieSlice, ...]
    note: str             # phrase affichée sous le graphique


@dataclass(frozen=True)
class FlowChartData:
    labels: list[str]            # un libellé de date par jour (ex. « 14 oct. »)
    deposits: list[int]          # entrées de chaque jour
    expenses: list[int]          # sorties de chaque jour
    deposits_text: str           # légende : « Entrées · 0 Ar »
    expenses_text: str           # légende : « Sorties · 60 000 Ar »
    note: str                    # phrase affichée sous le graphique
