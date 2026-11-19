from __future__ import annotations

from .....application.ports.inbound import EventSource, ManageLedger, ManageWallets
from ..contract.interfaces import Dialogs, HeaderListener, HeaderView
from ..parsing import parse_non_negative_int
from .base import Controller


class HeaderController(Controller, HeaderListener):
    """Barre du haut : choix du portefeuille, solde initial, import et ouverture du fichier de données."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: HeaderView, ledger: ManageLedger,
                 wallets: ManageWallets, app_title: str):
        super().__init__(events, dialogs)
        self._view = view
        self._ledger = ledger
        self._wallets = wallets
        self._app_title = app_title
        view.set_listener(self)

    def refresh(self) -> None:
        active = self._wallets.active_name()
        self._view.show_wallets(self._wallets.names(), active)
        self._view.show_initial_balance(str(self._ledger.initial_balance()))
        self._view.set_window_title(f"{self._app_title} — {active}")

    def on_catalog_changed(self) -> None:
        self.refresh()

    # ---- actions ------------------------------------------------------------------------------------
    def on_wallet_selected(self, name: str) -> None:
        if name == self._wallets.active_name():
            return
        with self.guard("Portefeuille illisible"):
            self._wallets.open(name)
        self.refresh()  # remet le sélecteur sur le portefeuille réellement ouvert (en cas d'échec)

    def on_apply_initial_balance(self) -> None:
        with self.guard("Solde initial"):
            self._ledger.set_initial_balance(parse_non_negative_int(self._view.get_initial_balance_text()))

    def on_import(self) -> None:
        path = self._dialogs.ask_open_file("Importer des transactions", self._ledger.import_patterns())
        if not path:
            return
        with self.guard("Import impossible"):
            preview = self._ledger.preview_import(path)
            message = f"Ajouter {len(preview.transactions)} transaction(s) ?"
            if preview.new_categories:
                message += f"\n\nNouvelles catégories créées : {', '.join(preview.new_categories)}"
            if not self._dialogs.confirm("Importer", message):
                return
            self._ledger.import_transactions(preview)

    def on_open_storage(self) -> None:
        with self.guard("Erreur"):
            self._ledger.open_storage_file()
