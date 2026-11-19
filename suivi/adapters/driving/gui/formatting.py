"""Mise en forme des valeurs pour l'AFFICHAGE (appartient à l'adaptateur graphique, pas au domaine)."""
import datetime as dt


def format_ar(n) -> str:
    return f"{int(round(n)):,}".replace(",", " ") + " Ar"


def format_number(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def format_date(day: dt.date) -> str:
    return day.strftime("%d/%m/%Y")


_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"]
_MONTHS_SHORT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def format_day_short(day: dt.date) -> str:
    """20 oct."""
    return f"{day.day} {_MONTHS_SHORT[day.month - 1]}"


def format_day_long(day: dt.date) -> str:
    """20 octobre"""
    return f"{day.day} {_MONTHS[day.month - 1]}"


def format_percent(value: float) -> str:
    """33,3 %"""
    return f"{value:.1f}".replace(".", ",") + " %"
