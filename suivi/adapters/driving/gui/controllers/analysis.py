from __future__ import annotations

from typing import Optional

from .....application.ports.inbound import AnalyzeSpending, EventSource, ManageCategories
from .....domain.model.period import Period
from .....domain.services.spending import SpendingAnalysis
from ..contract.dto import ChartData, Row
from ..contract.interfaces import AnalysisListener, AnalysisView, Dialogs
from ..formatting import format_ar, format_date
from ..parsing import InvalidInput, parse_amount, parse_date
from .base import Controller

_PLACEHOLDER = "Choisissez une catégorie et une période, puis cliquez sur « Analyser »."
_SUGGESTION_KEYS = ("serre", "equilibre", "confortable")


class AnalysisController(Controller, AnalysisListener):
    """Onglet « Analyse budget » : statistiques des dépenses journalières d'une catégorie,
    budgets proposés (moyenne, +½ écart-type, +1 écart-type) et graphique."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: AnalysisView, analysis: AnalyzeSpending,
                 categories: ManageCategories):
        super().__init__(events, dialogs)
        self._view = view
        self._analysis = analysis
        self._categories = categories
        self._result: Optional[SpendingAnalysis] = None
        self._period_ready = False
        view.set_listener(self)

    def reset(self) -> None:
        self._period_ready = False

    def refresh(self) -> None:
        categories = self._analysis.categories()
        self._view.set_categories(categories)
        if self._view.get_category() not in categories:
            self._view.set_category(categories[0] if categories else "")
        if not self._period_ready:  # par défaut : toute la période couverte par les données
            period = self._analysis.default_period()
            self._view.set_period(format_date(period.start), format_date(period.end))
            self._period_ready = True
        self._clear()

    def on_budgets_changed(self) -> None:
        self._show_current_budget()

    def _clear(self) -> None:
        self._result = None
        self._view.show_stats([])
        self._view.show_suggestions({k: "—" for k in _SUGGESTION_KEYS})
        self._view.show_diagnostic(_PLACEHOLDER)
        self._view.set_budget_text("")
        self._show_current_budget()
        self._draw()

    def _show_current_budget(self) -> None:
        category = self._view.get_category()
        current = self._analysis.daily_budget(category) if category else 0
        if current:
            text = f"Budget / jour actuel de « {category} » : {format_ar(current)}"
        else:
            text = f"Aucun budget / jour défini pour « {category} »." if category else ""
        self._view.show_current_budget(text)

    # ---- actions -----------------------------------------------------------------------------------
    def on_category_changed(self) -> None:
        self._clear()

    def on_analyze(self) -> None:
        with self.guard("Analyse"):
            category = self._view.get_category()
            if category not in self._analysis.categories():
                self._dialogs.info("Analyse", "Choisissez d'abord une catégorie.")
                return
            start, end = (parse_date(t) for t in self._view.get_period())
            result = self._analysis.analyze(category, Period(start, end))
            stats = result.stats
            self._result = result

            self._view.show_stats([Row(str(i), (name, value)) for i, (name, value) in enumerate([
                ("Nombre de jours analysés", stats.days),
                ("Jours avec dépense", stats.days_with_expense),
                ("Total des dépenses", format_ar(stats.total)),
                ("Moyenne par jour", format_ar(stats.mean)),
                ("Médiane par jour", format_ar(stats.median)),
                ("Écart-type", format_ar(stats.std)),
                ("Minimum / jour", format_ar(stats.minimum)),
                ("Maximum / jour", format_ar(stats.maximum)),
                ("Variabilité (écart-type / moyenne)", f"{stats.variability * 100:.0f} %"),
                ("Jours au-dessus de la moyenne", stats.days_above_mean)])])
            self._view.show_suggestions({k: format_ar(v) for k, v in stats.suggestions.items()})
            self._view.show_diagnostic(self._analysis.diagnose(stats))
            self._show_current_budget()
            self._view.set_budget_text(str(stats.suggestions["serre"]) if stats.total else "")  # la moyenne
            self._draw()

    def on_use_suggestion(self, key: str) -> None:
        if self._result is None:
            self._dialogs.info("Analyse", "Lancez d'abord l'analyse.")
            return
        self._view.set_budget_text(str(self._result.stats.suggestions[key]))

    def on_budget_edited(self) -> None:
        self._draw()

    def on_save_budget(self) -> None:
        if self._result is None:
            self._dialogs.info("Analyse", "Lancez d'abord l'analyse.")
            return
        with self.guard("Budget / jour"):
            value = parse_amount(self._view.get_budget_text())
            category = self._result.category
            self._categories.set_daily_budget(category, value)
            self._dialogs.info("Budget / jour", f"Budget / jour de « {category} » : {format_ar(value)}.\n"
                                                "Il sera utilisé dans l'onglet « Budget ».")

    # ---- graphique -----------------------------------------------------------------------------------
    def _retained(self) -> Optional[int]:
        try:
            return parse_amount(self._view.get_budget_text())
        except InvalidInput:
            return None

    def _draw(self) -> None:
        if self._result is None:
            self._view.draw_chart(None)
            return
        stats, retained = self._result.stats, self._retained()
        self._view.draw_chart(ChartData(
            labels=[day.strftime("%d/%m") for day, _v in self._result.daily],
            values=[v for _d, v in self._result.daily], mean=stats.mean, std=stats.std, retained=retained,
            mean_text=f"moyenne {format_ar(stats.mean)}",
            retained_text=(f"budget retenu {format_ar(retained)} (en orange : jours au-dessus)"
                           if retained is not None else None)))
