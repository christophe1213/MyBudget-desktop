from __future__ import annotations

from ..dto import CategoryInfo
from ..events import Event
from ..ports.inbound import ManageCategories
from ..session import LedgerSession


class CategoriesUseCase(ManageCategories):
    def __init__(self, session: LedgerSession):
        self._session = session

    def list_categories(self) -> list[CategoryInfo]:
        ledger = self._session.ledger
        return [CategoryInfo(c, ledger.category_usage(c), ledger.daily_budget(c)) for c in ledger.categories]

    def add(self, name: str) -> None:
        self._session.apply(lambda ledger: ledger.add_category(name))

    def rename(self, old: str, new: str) -> None:
        self._session.apply(lambda ledger: ledger.rename_category(old, new))

    def remove(self, name: str) -> None:
        self._session.apply(lambda ledger: ledger.remove_category(name))

    def daily_budget(self, category: str) -> int:
        return self._session.ledger.daily_budget(category)

    def set_daily_budget(self, category: str, amount: int) -> None:
        self._session.apply(lambda ledger: ledger.set_daily_budget(category, amount), Event.BUDGETS_CHANGED)

    def has_daily_budgets(self) -> bool:
        return bool(self._session.ledger.budgets)
