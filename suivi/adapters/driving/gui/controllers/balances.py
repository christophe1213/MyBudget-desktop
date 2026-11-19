from __future__ import annotations

from .....application.ports.inbound import EventSource, QueryBalances
from ..contract.dto import ALL, Row
from ..contract.interfaces import BalanceView, CategoryDetailListener, CategoryDetailView, Dialogs
from ..formatting import format_ar, format_date
from .base import Controller


class BalanceController(Controller):
    """Onglet « Solde par date »."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: BalanceView, balances: QueryBalances):
        super().__init__(events, dialogs)
        self._view = view
        self._balances = balances

    def refresh(self) -> None:
        self._view.show_rows([
            Row(str(i), (format_date(r.date), format_ar(r.deposits), format_ar(r.expenses),
                         format_ar(r.balance)))
            for i, r in enumerate(self._balances.balance_by_date())])


class CategoryDetailController(Controller, CategoryDetailListener):
    """Onglet « Détail par catégorie » : dépôts, dépenses et solde par date et par catégorie."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: CategoryDetailView,
                 balances: QueryBalances):
        super().__init__(events, dialogs)
        self._view = view
        self._balances = balances
        view.set_listener(self)

    def refresh(self) -> None:
        categories = self._balances.categories()
        dates = [format_date(d) for d in self._balances.transaction_dates()]
        category, date = self._view.get_filters()
        if category not in [ALL] + categories:
            category = ALL
        if date not in [ALL] + dates:
            date = ALL
        self._view.set_filter_options([ALL] + categories, [ALL] + dates)
        self._view.set_filters(category, date)
        self._show(category, date)

    def on_filter_changed(self) -> None:
        self._show(*self._view.get_filters())

    def _show(self, category: str, date: str) -> None:
        details = self._balances.category_balances()
        if category != ALL:
            details = [r for r in details if r.category == category]
        if date != ALL:
            details = [r for r in details if format_date(r.date) == date]
        self._view.show_rows([
            Row(str(i), (format_date(r.date), r.category, format_ar(r.deposits), format_ar(r.expenses),
                         format_ar(r.net), format_ar(r.balance)))
            for i, r in enumerate(details)])
        self._view.show_totals(
            f"Total affiché — dépôts : {format_ar(sum(r.deposits for r in details))}   "
            f"dépenses : {format_ar(sum(r.expenses for r in details))}   "
            f"net : {format_ar(sum(r.net for r in details))}")
