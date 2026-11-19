from __future__ import annotations

from .....application.ports.inbound import EventSource, ManageTransactions
from ..contract.dto import Row, Tab
from ..contract.interfaces import Dialogs, Navigator, TransactionsListener, TransactionsView
from ..formatting import format_ar, format_date
from ..parsing import InvalidInput, parse_amount, parse_date, parse_kind
from .base import Controller


class TransactionsController(Controller, TransactionsListener):
    """Onglet « Saisie » : ajouter / supprimer des transactions, voir celles d'un jour."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: TransactionsView,
                 navigator: Navigator, transactions: ManageTransactions):
        super().__init__(events, dialogs)
        self._view = view
        self._navigator = navigator
        self._transactions = transactions
        view.set_listener(self)

    def refresh(self) -> None:
        categories = self._transactions.categories()
        self._view.set_categories(categories)
        if self._view.get_category() not in categories:
            self._view.set_category(categories[0] if categories else "")
        self._show_day()

    # ---- actions de l'utilisateur ---------------------------------------------------------------
    def on_add(self) -> None:
        if not self._transactions.categories():
            self._dialogs.info("Catégories",
                               "Ajoutez d'abord au moins une catégorie (onglet « Catégories »).")
            self._navigator.show_tab(Tab.CATEGORIES)
            return
        with self.guard("Saisie invalide"):
            form = self._view.get_form()
            self._transactions.add(parse_date(form.date), form.category.strip(), parse_kind(form.kind),
                                   form.label, parse_amount(form.amount))
            self._view.clear_entry()

    def on_delete(self) -> None:
        ids = self._view.get_selected_ids()
        if not ids:
            return
        if not self._dialogs.confirm("Supprimer", f"Supprimer {len(ids)} transaction(s) ?"):
            return
        with self.guard():
            self._transactions.delete([int(i) for i in ids])

    def on_date_changed(self) -> None:
        self._show_day()

    # ---- affichage -----------------------------------------------------------------------------------
    def _show_day(self) -> None:
        try:
            day = parse_date(self._view.get_date_text())
        except InvalidInput:
            self._view.show_day("Date invalide", [])
            return
        rows = [Row(str(i), (t.category, t.kind.value, t.label, format_ar(t.amount)))
                for i, t in self._transactions.transactions_on(day)]
        balance = format_ar(self._transactions.balance_at(day))
        self._view.show_day(f"Transactions du {format_date(day)} — solde à cette date : {balance}", rows)
