"""Analyse des dépenses journalières d'une catégorie pour définir un budget par jour (Python pur)."""
from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass

from ..model.ledger import Ledger
from ..model.period import Period
from ..model.transaction import Kind


@dataclass(frozen=True)
class SpendingStats:
    days: int
    days_with_expense: int
    total: int
    mean: float
    median: float
    std: float
    minimum: int
    maximum: int
    variability: float            # écart-type / moyenne
    days_above_mean: int
    suggestions: dict             # "serre" | "equilibre" | "confortable" -> montant arrondi à 100 Ar


@dataclass(frozen=True)
class SpendingAnalysis:
    category: str
    period: Period
    daily: tuple[tuple[dt.date, int], ...]   # (jour, dépense) pour CHAQUE jour de la période
    stats: SpendingStats


class SpendingAnalyzer:
    def analyze(self, ledger: Ledger, category: str, period: Period) -> SpendingAnalysis:
        per_day = {day: 0 for day in period.each_day()}   # les jours sans dépense comptent pour 0
        for t in ledger.transactions:
            if t.category == category and t.kind is Kind.EXPENSE and period.contains(t.date):
                per_day[t.date] += t.amount
        daily = tuple(per_day.items())
        return SpendingAnalysis(category, period, daily, self._statistics([v for _d, v in daily]))

    @staticmethod
    def _round_100(x: float) -> int:
        return int(x / 100 + 0.5) * 100

    def _statistics(self, values: list[int]) -> SpendingStats:
        mean = statistics.fmean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0   # écart-type de l'échantillon
        return SpendingStats(
            days=len(values), days_with_expense=sum(1 for v in values if v > 0), total=sum(values),
            mean=mean, median=float(statistics.median(values)), std=std, minimum=min(values),
            maximum=max(values), variability=(std / mean) if mean > 0 else 0.0,
            days_above_mean=sum(1 for v in values if v > mean),
            suggestions={"serre": self._round_100(mean),
                         "equilibre": self._round_100(mean + 0.5 * std),
                         "confortable": self._round_100(mean + std)})

    def diagnose(self, stats: SpendingStats) -> str:
        if stats.total == 0:
            return "Aucune dépense sur cette période : impossible de proposer un budget."
        if stats.variability < 0.7:
            return ("Dépenses régulières : la moyenne est un bon budget journalier, "
                    "les autres niveaux ajoutent peu.")
        if stats.variability < 1.5:
            return ("Dépenses assez variables : la moyenne reste la bonne base, car le solde de la "
                    "catégorie se reporte d'un jour à l'autre. Choisissez « équilibré » si vous voulez "
                    "une petite marge de sécurité.")
        return ("Dépenses très irrégulières (gros achats ponctuels) : prenez la moyenne comme budget. "
                "Le solde reporté absorbe les pics ; le niveau « confortable » serait bien trop élevé "
                "pour un jour ordinaire.")
