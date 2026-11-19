"""Fabrique de l'interface customtkinter : fenêtre, barre latérale verte, pages et vues."""
from __future__ import annotations

import customtkinter as ctk

from ..contract.dto import Tab
from ..contract.interfaces import Navigator, Screens, UserInterface
from . import theme as t
from .account_view import CtkAccountView
from .analysis_view import CtkAnalysisView
from .auth_view import CtkAuthView
from .balances_view import CtkBalanceView, CtkCategoryDetailView
from .budget_view import CtkBudgetView
from .dashboard_view import CtkDashboardView
from .categories_view import CtkCategoryManagerView
from .dialogs import CtkDialogs
from .header_view import CtkHeaderView
from .report_view import CtkReportView
from .sync_view import CtkSyncView
from .transactions_view import CtkTransactionsView
from .wallets_view import CtkWalletsView
from .widgets import apply_table_style, label

_PAGES = {
    Tab.DASHBOARD: ("Tableau de bord", "Où en sont vos budgets et comment l'argent circule"),
    Tab.ENTRY: ("Saisie", "Enregistrez vos dépôts et vos dépenses"),
    Tab.BALANCES: ("Solde par date", "Évolution de votre solde jour après jour"),
    Tab.CATEGORY_DETAILS: ("Détail par catégorie", "Dépôts, dépenses et solde de chaque catégorie"),
    Tab.CATEGORIES: ("Catégories", "Organisez vos dépenses par catégorie"),
    Tab.REPORT: ("Rapport", "Totaux par catégorie entre deux dates"),
    Tab.BUDGET: ("Budget", "Calculez et déposez le budget d'une période"),
    Tab.ANALYSIS: ("Analyse budget", "Trouvez le bon budget journalier d'une catégorie"),
    Tab.WALLETS: ("Portefeuilles", "Un portefeuille = un livre de comptes (banque, caisse…)"),
    Tab.SYNC: ("Synchronisation", "Configuration du partage entre appareils"),
}


class CtkNavigator(Navigator):
    """Affiche une page et met en évidence son bouton dans la barre latérale."""

    def __init__(self, pages: dict, buttons: dict):
        self._pages, self._buttons = pages, buttons

    def show_tab(self, tab: Tab) -> None:
        for other, page in self._pages.items():
            page.grid_remove()
            self._buttons[other].configure(fg_color="transparent", text_color=t.WHITE, hover_color=t.SIDEBAR_HOVER)
        self._pages[tab].grid(row=0, column=0, sticky="nsew")
        self._buttons[tab].configure(fg_color=t.WHITE, text_color=t.GREEN, hover_color=t.WHITE)


class CtkScreens(Screens):
    """Affiche soit l'écran d'authentification, soit l'application (jamais les deux)."""

    def __init__(self, auth_frame, app_frame):
        self._auth, self._app = auth_frame, app_frame

    def show_login(self) -> None:
        self._app.grid_remove()
        self._auth.grid(row=0, column=0, sticky="nsew")

    def show_app(self) -> None:
        self._auth.grid_remove()
        self._app.grid(row=0, column=0, sticky="nsew")


class CtkUserInterface(UserInterface):
    def __init__(self, title: str = "Suivi des transactions"):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")
        self.root = ctk.CTk(fg_color=t.WHITE)
        self.root.title(title)
        self.root.geometry("1240x800")
        self.root.minsize(1060, 680)
        apply_table_style()

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        app_frame = ctk.CTkFrame(self.root, fg_color=t.WHITE, corner_radius=0)
        app_frame.grid(row=0, column=0, sticky="nsew")
        auth_frame = ctk.CTkFrame(self.root, fg_color=t.WHITE, corner_radius=0)
        app_frame.grid_columnconfigure(1, weight=1)
        app_frame.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(app_frame, width=232, fg_color=t.GREEN, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        main = ctk.CTkFrame(app_frame, fg_color=t.WHITE, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(main, fg_color=t.WHITE, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        ctk.CTkFrame(main, height=1, fg_color=t.BORDER, corner_radius=0).grid(row=1, column=0, sticky="ew")
        content = ctk.CTkFrame(main, fg_color=t.WHITE, corner_radius=0)
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(sidebar, text="Repère", font=t.font(30, "bold"), text_color=t.WHITE, anchor="w").pack(
            anchor="w", padx=26, pady=(30, 0))
        ctk.CTkLabel(sidebar, text="suivi de vos comptes", font=t.font(13), text_color=t.SIDEBAR_MUTED,
                     anchor="w").pack(anchor="w", padx=26, pady=(0, 26))

        pages, buttons, bodies = {}, {}, {}
        for tab, (title_text, subtitle) in _PAGES.items():
            page = ctk.CTkFrame(content, fg_color=t.WHITE, corner_radius=0)
            label(page, title_text, "title").pack(anchor="w", padx=32, pady=(24, 0))
            label(page, subtitle, "muted").pack(anchor="w", padx=32, pady=(0, 16))
            body = ctk.CTkFrame(page, fg_color=t.WHITE, corner_radius=0)
            body.pack(fill="both", expand=True, padx=32, pady=(0, 24))
            pages[tab], bodies[tab] = page, body
            buttons[tab] = ctk.CTkButton(
                sidebar, text=f"   {title_text}", anchor="w", height=42, corner_radius=8, fg_color="transparent",
                text_color=t.WHITE, hover_color=t.SIDEBAR_HOVER, font=t.font(14, "bold"),
                command=lambda target=tab: self.navigator.show_tab(target))
            buttons[tab].pack(fill="x", padx=16, pady=2)
        ctk.CTkLabel(sidebar, text="Montants en Ariary (Ar)", font=t.font(12), text_color=t.SIDEBAR_MUTED).pack(
            side="bottom", pady=20)

        self.account = CtkAccountView(sidebar)
        self.auth = CtkAuthView(auth_frame)
        self.screens = CtkScreens(auth_frame, app_frame)
        self.dialogs = CtkDialogs(self.root)
        self.navigator = CtkNavigator(pages, buttons)
        self.header = CtkHeaderView(self.root, header_frame)
        self.dashboard = CtkDashboardView(bodies[Tab.DASHBOARD])
        self.transactions = CtkTransactionsView(bodies[Tab.ENTRY])
        self.balances = CtkBalanceView(bodies[Tab.BALANCES])
        self.category_details = CtkCategoryDetailView(bodies[Tab.CATEGORY_DETAILS])
        self.categories = CtkCategoryManagerView(bodies[Tab.CATEGORIES])
        self.report = CtkReportView(bodies[Tab.REPORT])
        self.budget = CtkBudgetView(bodies[Tab.BUDGET])
        self.analysis = CtkAnalysisView(bodies[Tab.ANALYSIS])
        self.wallets = CtkWalletsView(bodies[Tab.WALLETS])
        self.sync = CtkSyncView(bodies[Tab.SYNC])
        self.navigator.show_tab(Tab.DASHBOARD)

    def run(self) -> None:
        self.root.mainloop()
