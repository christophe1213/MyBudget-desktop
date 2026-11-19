from __future__ import annotations

import datetime as dt
from typing import Optional

from .....application.ports.inbound import EventSource, ViewDashboard
from .....domain.model.errors import DomainError
from .....domain.model.period import Period
from .....domain.services.dashboard import BudgetShares, FlowSeries
from ..contract.dto import FlowChartData, PieData, PieSlice
from ..contract.interfaces import Dialogs, DashboardListener, DashboardView
from ..formatting import format_ar, format_date, format_day_long, format_day_short, format_percent
from ..parsing import InvalidInput, parse_date
from .base import Controller


class DashboardController(Controller, DashboardListener):
    """Tableau de bord : soldes restants par budget (camembert) et entrées / sorties par jour (courbes),
    avec un filtre entre deux dates sur le graphique des flux."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: DashboardView, dashboard: ViewDashboard):
        super().__init__(events, dialogs)
        self._view = view
        self._dashboard = dashboard
        self._period_ready = False
        view.set_listener(self)

    def reset(self) -> None:
        self._period_ready = False   # un autre portefeuille : on repart de sa propre période par défaut

    def on_imported(self) -> None:
        self._period_ready = False   # de nouvelles données : la période par défaut doit les couvrir
        self.refresh()

    def refresh(self) -> None:
        self._view.show_budget_shares(self._pie(self._dashboard.budget_shares()))
        if not self._period_ready:   # premier affichage : période par défaut
            period = self._dashboard.default_period()
            self._set_period(period)
            self._period_ready = True
            self._show_flows(period)
            return
        try:   # ensuite, on garde la période choisie par l'utilisateur quand les données changent
            self._show_flows(self._read_period())
        except (InvalidInput, DomainError):
            pass   # saisie en cours d'édition : on laisse le graphique tel quel

    # ---- actions ------------------------------------------------------------------------------------
    def on_apply_filter(self) -> None:
        with self.guard("Période"):
            self._show_flows(self._read_period())

    def on_preset(self, days: Optional[int]) -> None:
        data = self._dashboard.data_period()
        if data is None:
            period = self._dashboard.default_period()
        elif days is None:
            period = data
        else:
            period = Period(max(data.start, data.end - dt.timedelta(days=days - 1)), data.end)
        self._set_period(period)
        with self.guard("Période"):
            self._show_flows(period)

    # ---- affichage ------------------------------------------------------------------------------------
    def _read_period(self) -> Period:
        start, end = (parse_date(t) for t in self._view.get_period())
        return Period(start, end)

    def _set_period(self, period: Period) -> None:
        self._view.set_period(format_date(period.start), format_date(period.end))

    @staticmethod
    def _pie(shares: BudgetShares) -> Optional[PieData]:
        if not shares.items:
            return None
        slices = tuple(PieSlice(i.category, i.balance, format_ar(i.balance), format_percent(i.share))
                       for i in shares.items)
        note = f"Base : {format_ar(shares.total)} de soldes restants répartis sur {len(slices)} budget(s)."
        if shares.deficits:
            names = ", ".join(name for name, _amount in shares.deficits)
            note += (f" Les {format_ar(shares.deficit_total)} en déficit ({names}) ne font pas partie du "
                     "camembert.")
        return PieData(slices, note)

    def _show_flows(self, period: Period) -> None:
        series: FlowSeries = self._dashboard.flows(period)
        parts = ["Montants par jour, en Ar."]
        if series.peak_expense_day is not None:
            detail = " + ".join(f"{category} {format_ar(amount)}" for category, amount in series.peak_expense_breakdown)
            parts.append(f"Le {format_day_long(series.peak_expense_day.date)} : {detail}.")
        else:
            parts.append("Aucune sortie sur cette période.")
        if series.peak_deposit_day is None:
            parts.append("Entrées : 0 Ar à chaque date.")
        else:
            parts.append(f"Plus forte entrée : le {format_day_long(series.peak_deposit_day.date)} "
                         f"({format_ar(series.peak_deposit_day.deposits)}).")
        self._view.show_flows(FlowChartData(
            labels=[format_day_short(d.date) for d in series.days],
            deposits=[d.deposits for d in series.days], expenses=[d.expenses for d in series.days],
            deposits_text=f"Entrées · {format_ar(series.total_deposits)}",
            expenses_text=f"Sorties · {format_ar(series.total_expenses)}", note=" ".join(parts)))
