from __future__ import annotations

import os

from .....application.ports.inbound import EventSource, ManageWallets
from ..contract.dto import Row, Tab
from ..contract.interfaces import Dialogs, Navigator, WalletsListener, WalletsView
from ..formatting import format_ar
from .base import Controller


class WalletsController(Controller, WalletsListener):
    """Onglet « Portefeuilles » : un portefeuille = un livre de comptes, avec son propre stockage."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: WalletsView, wallets: ManageWallets,
                 navigator: Navigator):
        super().__init__(events, dialogs)
        self._view = view
        self._wallets = wallets
        self._navigator = navigator
        self._names: list[str] = []
        view.set_listener(self)

    def refresh(self) -> None:
        summaries = self._wallets.summaries()
        self._names = [s.name for s in summaries]
        rows, total = [], 0
        for i, s in enumerate(summaries):
            mark = "● " if s.active else ""
            if s.balance is None:
                rows.append(Row(str(i), (mark + s.name, s.location, "—", "introuvable")))
            else:
                total += s.balance
                rows.append(Row(str(i), (mark + s.name, s.location, s.transaction_count, format_ar(s.balance))))
        self._view.show_wallets(rows, f"Solde total de tous les portefeuilles : {format_ar(total)}")

    def on_catalog_changed(self) -> None:
        self.refresh()

    def _selected_name(self, interactive: bool = True):
        selected = self._view.get_selected_id()
        if selected is None:
            if interactive:
                self._dialogs.info("Portefeuilles", "Sélectionnez d'abord un portefeuille dans la liste.")
            return None
        return self._names[int(selected)]

    # ---- actions ------------------------------------------------------------------------------------
    def on_open(self, interactive: bool = True) -> None:
        name = self._selected_name(interactive)
        if name is None:
            return
        with self.guard("Portefeuille illisible"):
            self._wallets.open(name)
            self._navigator.show_tab(Tab.ENTRY)

    def on_new(self) -> None:
        name = self._dialogs.ask_text("Nouveau portefeuille", "Nom du portefeuille (ex. Banque, Caisse) :")
        if name is None:
            return
        with self.guard("Portefeuilles"):
            ref = self._wallets.create(name.strip())
            self._navigator.show_tab(Tab.CATEGORIES)  # à remplir pour ce portefeuille
            self._dialogs.info("Portefeuille créé",
                               f"Portefeuille « {ref.name} » créé ({ref.location}).\n"
                               "Ajoutez ses catégories dans l'onglet « Catégories ».")

    def on_link_file(self) -> None:
        path = self._dialogs.ask_open_file("Choisir un fichier de transactions", self._wallets.link_patterns())
        if not path:
            return
        with self.guard("Portefeuilles"):
            location = self._wallets.prepare_link(path)
            name = self._dialogs.ask_text("Nom du portefeuille", "Nom du portefeuille :",
                                          os.path.splitext(os.path.basename(path))[0])
            if name is None:
                return
            self._wallets.link(name.strip(), location)

    def on_rename(self) -> None:
        old = self._selected_name()
        if old is None:
            return
        new = self._dialogs.ask_text("Renommer", f"Nouveau nom pour « {old} » :", old)
        if new is None or new.strip() == old:
            return
        with self.guard("Portefeuilles"):
            self._wallets.rename(old, new.strip())

    def on_remove(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        if len(self._names) == 1:
            self._dialogs.warning("Portefeuilles", "Impossible de retirer le dernier portefeuille.")
            return
        if not self._dialogs.confirm("Retirer", f"Retirer « {name} » de la liste ?\n"
                                                 "Le stockage du portefeuille n'est pas supprimé."):
            return
        with self.guard("Portefeuilles"):
            self._wallets.remove(name)
