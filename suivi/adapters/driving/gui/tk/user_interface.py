"""Fabrique abstraite : assemble la fenêtre tkinter et toutes ses vues."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..contract.dto import Tab
from ..contract.interfaces import Navigator, UserInterface
from .analysis_view import TkAnalysisView
from .balances_view import TkBalanceView, TkCategoryDetailView
from .budget_view import TkBudgetView
from .dashboard_view import TkDashboardView
from .categories_view import TkCategoryManagerView
from .dialogs import TkDialogs
from .header_view import TkHeaderView
from .report_view import TkReportView
from .sync_view import TkSyncView
from .transactions_view import TkTransactionsView
from .wallets_view import TkWalletsView

_TITLES = {Tab.DASHBOARD: "Tableau de bord", Tab.ENTRY: "Saisie", Tab.BALANCES: "Solde par date",
           Tab.CATEGORY_DETAILS: "Détail par catégorie", Tab.CATEGORIES: "Catégories", Tab.REPORT: "Rapport",
           Tab.BUDGET: "Budget", Tab.ANALYSIS: "Analyse budget", Tab.WALLETS: "Portefeuilles",
           Tab.SYNC: "Synchronisation"}


class TkNavigator(Navigator):
    def __init__(self, notebook: ttk.Notebook, frames: dict):
        self._notebook, self._frames = notebook, frames

    def show_tab(self, tab: Tab) -> None:
        self._notebook.select(self._frames[tab])


class TkUserInterface(UserInterface):
    def __init__(self, title: str = "Suivi des transactions"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1020x700")
        self.root.minsize(880, 580)

        header_frame = ttk.Frame(self.root, padding=(10, 8))
        header_frame.pack(fill="x")
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        frames = {}
        for tab in Tab:  # l'ordre de l'énumération = l'ordre des onglets
            frames[tab] = ttk.Frame(notebook, padding=10)
            notebook.add(frames[tab], text=_TITLES[tab])

        self.dialogs = TkDialogs(self.root)
        self.navigator = TkNavigator(notebook, frames)
        self.header = TkHeaderView(self.root, header_frame)
        self.dashboard = TkDashboardView(frames[Tab.DASHBOARD])
        self.transactions = TkTransactionsView(frames[Tab.ENTRY])
        self.balances = TkBalanceView(frames[Tab.BALANCES])
        self.category_details = TkCategoryDetailView(frames[Tab.CATEGORY_DETAILS])
        self.categories = TkCategoryManagerView(frames[Tab.CATEGORIES])
        self.report = TkReportView(frames[Tab.REPORT])
        self.budget = TkBudgetView(frames[Tab.BUDGET])
        self.analysis = TkAnalysisView(frames[Tab.ANALYSIS])
        self.wallets = TkWalletsView(frames[Tab.WALLETS])
        self.sync = TkSyncView(frames[Tab.SYNC])

    def run(self) -> None:
        self.root.mainloop()
