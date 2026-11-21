"""RACINE DE COMPOSITION : le seul endroit qui connaît les classes concrètes et les assemble.

  adaptateur pilotant (interface) ──► ports entrants ──► cas d'usage ──► domaine
                                                              │
                                                       ports sortants ◄── adaptateurs pilotés (stockage...)

Changer de stockage  : passer d'autres `DrivenPorts` (ex. `sqlite_ports`).
Changer d'interface  : passer une autre implémentation de `UserInterface` (ex. customtkinter).
Authentification     : `auth_ports` (comptes) est indépendant de `ports` (données financières).
"""
from __future__ import annotations

from .adapters.driving.gui.contract.interfaces import SyncView, UserInterface
from .adapters.driving.gui.controllers.analysis import AnalysisController
from .adapters.driving.gui.controllers.auth import AuthController
from .adapters.driving.gui.controllers.balances import BalanceController, CategoryDetailController
from .adapters.driving.gui.controllers.base import Controller
from .adapters.driving.gui.controllers.budget import BudgetController
from .adapters.driving.gui.controllers.categories import CategoriesController
from .adapters.driving.gui.controllers.dashboard import DashboardController
from .adapters.driving.gui.controllers.header import HeaderController
from .adapters.driving.gui.controllers.report import ReportController
from .adapters.driving.gui.controllers.sync import SyncController
from .adapters.driving.gui.controllers.transactions import TransactionsController
from .adapters.driving.gui.controllers.wallets import WalletsController
from .application.events import EventEmitter
from .application.ports.inbound import ManageWallets
from .application.dto import UserInfo
from .application.ports.outbound import AuthPorts, DrivenPorts, SyncJournal
from .application.session import LedgerSession
from .application.use_cases.analysis import AnalysisUseCase
from .application.use_cases.auth import AuthService
from .application.use_cases.balances import BalancesUseCase
from .application.use_cases.budgets import BudgetsUseCase
from .application.use_cases.categories import CategoriesUseCase
from .application.use_cases.dashboard import DashboardUseCase
from .application.use_cases.reports import ReportsUseCase
from .application.use_cases.settings import LedgerUseCase
from .application.use_cases.sync import SyncUseCase
from .application.use_cases.transactions import TransactionsUseCase
from .application.use_cases.wallets import WalletsUseCase
from .domain.services.balances import BalanceCalculator
from .domain.services.budget import BudgetPlanner
from .domain.services.dashboard import DashboardAnalyzer
from .domain.services.reports import ReportBuilder
from .domain.services.spending import SpendingAnalyzer


class Application:
    def __init__(self, ui: UserInterface, wallets: ManageWallets, controllers: list[Controller]):
        self.ui = ui
        self.wallets = wallets
        self.controllers = controllers
        self.auth_controller: AuthController | None = None   # absent : l'application démarre sans connexion
        self._main_started = False

    def start(self) -> None:
        """Avec authentification : affiche l'écran de connexion (ou reconnecte). Sinon : ouvre l'application."""
        if self.auth_controller is None:
            self._start_main()
        else:
            self.auth_controller.start()

    def on_login(self, _user: UserInfo) -> None:
        """Appelé après une connexion réussie : les données ne sont chargées qu'à ce moment-là."""
        try:
            self._start_main()
        except Exception as e:  # noqa: BLE001
            self.ui.dialogs.error("Démarrage impossible", f"Impossible d'ouvrir le portefeuille actif :\n{e}")
            if self.ui.screens is not None:
                self.ui.screens.show_login()

    def _start_main(self) -> None:
        if self._main_started:
            return
        self.wallets.start()
        for controller in self.controllers:
            controller.start()
        self._main_started = True

    def run(self) -> None:
        try:
            self.start()
        except Exception as e:  # noqa: BLE001
            self.ui.dialogs.error("Démarrage impossible", f"Impossible d'ouvrir le portefeuille actif :\n{e}")
            return
        self.ui.run()


def build_application(ui: UserInterface, ports: DrivenPorts, export_dir: str,
                      app_title: str = "Suivi des transactions",
                      auth_ports: AuthPorts | None = None,
                      sync_journal: SyncJournal | None = None) -> Application:
    events = EventEmitter()
    balances, reports = BalanceCalculator(), ReportBuilder()
    planner, analyzer = BudgetPlanner(), SpendingAnalyzer()

    # application : session + cas d'usage (implémentent les ports entrants)
    session = LedgerSession(ports.ledgers, events)
    wallets = WalletsUseCase(ports.registry, ports.ledgers, ports.locations, balances, session, events)
    ledger = LedgerUseCase(session, ports.importer, ports.locations, ports.opener)
    transactions = TransactionsUseCase(session, balances)
    categories = CategoriesUseCase(session)
    queries = BalancesUseCase(session, balances)
    report_use_case = ReportsUseCase(session, reports, ports.exporter, ports.opener, ports.clock, wallets)
    budgets = BudgetsUseCase(session, planner, ports.clock)
    analysis = AnalysisUseCase(session, analyzer, ports.clock)
    dashboard = DashboardUseCase(session, DashboardAnalyzer(), ports.clock)

    # adaptateur pilotant : un contrôleur par vue, qui ne connaît que les ports entrants
    d, nav = ui.dialogs, ui.navigator
    controllers: list[Controller] = [
        HeaderController(events, d, ui.header, ledger, wallets, app_title),
        DashboardController(events, d, ui.dashboard, dashboard),
        TransactionsController(events, d, ui.transactions, nav, transactions),
        BalanceController(events, d, ui.balances, queries),
        CategoryDetailController(events, d, ui.category_details, queries),
        CategoriesController(events, d, ui.categories, categories),
        ReportController(events, d, ui.report, report_use_case, export_dir),
        BudgetController(events, d, ui.budget, budgets, categories),
        AnalysisController(events, d, ui.analysis, analysis, categories),
        WalletsController(events, d, ui.wallets, wallets, nav),
    ]
    # synchronisation (facultative : seulement avec un journal ET une vue qui sait l'afficher)
    if sync_journal is not None and isinstance(getattr(ui, "sync", None), SyncView):
        sync = SyncUseCase(session, wallets, ports.ledgers, sync_journal, ports.clock, events)
        controllers.append(SyncController(events, d, ui.sync, sync))
    application = Application(ui, wallets, controllers)

    # authentification (facultative : seulement si on fournit ses adaptateurs ET que l'interface sait l'afficher)
    if auth_ports is not None and ui.auth is not None and ui.account is not None and ui.screens is not None:
        auth = AuthService(auth_ports.accounts, auth_ports.hasher, auth_ports.tokens, auth_ports.local, ports.clock)
        application.auth_controller = AuthController(d, ui.auth, ui.account, auth, ui.screens, application.on_login)
    return application
