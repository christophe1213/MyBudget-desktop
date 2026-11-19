from __future__ import annotations

from .....application.ports.inbound import EventSource, ManageCategories
from ..contract.dto import Row
from ..contract.interfaces import CategoryManagerListener, CategoryManagerView, Dialogs
from ..formatting import format_ar
from .base import Controller


class CategoriesController(Controller, CategoryManagerListener):
    """Onglet « Catégories » : ajouter, renommer, supprimer."""

    def __init__(self, events: EventSource, dialogs: Dialogs, view: CategoryManagerView,
                 categories: ManageCategories):
        super().__init__(events, dialogs)
        self._view = view
        self._categories = categories
        self._shown = []   # catégories affichées, dans l'ordre (l'identifiant d'une ligne = sa position)
        view.set_listener(self)

    def refresh(self) -> None:
        self._shown = self._categories.list_categories()
        self._view.show_categories([
            Row(str(i), (c.name, c.usage, format_ar(c.daily_budget) if c.daily_budget else "—"))
            for i, c in enumerate(self._shown)])

    def on_budgets_changed(self) -> None:
        self.refresh()

    def _selected(self):
        selected = self._view.get_selected_id()
        if selected is None:
            self._dialogs.info("Catégories", "Sélectionnez d'abord une catégorie dans la liste.")
            return None
        return self._shown[int(selected)]

    def on_add(self) -> None:
        name = self._view.get_new_name().strip()
        if not name:
            return
        with self.guard("Catégories"):
            self._categories.add(name)
            self._view.clear_new_name()

    def on_rename(self) -> None:
        category = self._selected()
        if category is None:
            return
        new = self._dialogs.ask_text("Renommer", f"Nouveau nom pour « {category.name} » :", category.name)
        if new is None or not new.strip() or new.strip() == category.name:
            return
        with self.guard("Catégories"):
            self._categories.rename(category.name, new)

    def on_delete(self) -> None:
        category = self._selected()
        if category is None:
            return
        if category.usage:
            self._dialogs.warning(
                "Suppression impossible",
                f"La catégorie « {category.name} » est utilisée par {category.usage} transaction(s).\n"
                "Renommez-la, ou supprimez d'abord ces transactions.")
            return
        if not self._dialogs.confirm("Supprimer", f"Supprimer la catégorie « {category.name} » ?"):
            return
        with self.guard("Catégories"):
            self._categories.remove(category.name)
