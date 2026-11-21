"""Contrats des vues de l'adaptateur graphique (« vue passive »).

Chaque vue expose :
  - des méthodes d'AFFICHAGE appelées par le contrôleur (`show_...`, `set_...`),
  - des méthodes de LECTURE de ce que l'utilisateur a saisi (`get_...`),
  - un `Listener` : l'interface que la vue appelle quand l'utilisateur agit.

Le contrôleur n'importe jamais tkinter ni customtkinter : pour changer de bibliothèque graphique,
il suffit d'écrire une nouvelle implémentation de ces interfaces (voir views/tk/ et UserInterface).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .dto import AuthForm, AuthMode, ChartData, FlowChartData, PieData, Row, Tab, TransactionForm


# ---------------------------------------------------------------- services transverses
class Dialogs(ABC):
    @abstractmethod
    def info(self, title: str, message: str) -> None: ...

    @abstractmethod
    def warning(self, title: str, message: str) -> None: ...

    @abstractmethod
    def error(self, title: str, message: str) -> None: ...

    @abstractmethod
    def confirm(self, title: str, message: str) -> bool: ...

    @abstractmethod
    def ask_text(self, title: str, prompt: str, initial: str = "") -> Optional[str]: ...

    @abstractmethod
    def ask_int(self, title: str, prompt: str, initial: int = 0, minimum: int = 0) -> Optional[int]: ...

    @abstractmethod
    def ask_open_file(self, title: str, patterns: Sequence[str] = ()) -> Optional[str]:
        """Choix d'un fichier existant ; `patterns` = types proposés en priorité (ex. ('*.xlsx',))."""

    @abstractmethod
    def ask_save_file(self, title: str, initial_dir: str, initial_name: str) -> Optional[str]: ...


class Navigator(ABC):
    @abstractmethod
    def show_tab(self, tab: Tab) -> None: ...


# ---------------------------------------------------------------- en-tête
class HeaderListener(ABC):
    @abstractmethod
    def on_wallet_selected(self, name: str) -> None: ...

    @abstractmethod
    def on_apply_initial_balance(self) -> None: ...

    @abstractmethod
    def on_import(self) -> None: ...

    @abstractmethod
    def on_open_storage(self) -> None: ...


class HeaderView(ABC):
    @abstractmethod
    def set_listener(self, listener: HeaderListener) -> None: ...

    @abstractmethod
    def show_wallets(self, names: Sequence[str], active: str) -> None: ...

    @abstractmethod
    def show_initial_balance(self, text: str) -> None: ...

    @abstractmethod
    def get_initial_balance_text(self) -> str: ...

    @abstractmethod
    def set_window_title(self, text: str) -> None: ...


# ---------------------------------------------------------------- saisie
class TransactionsListener(ABC):
    @abstractmethod
    def on_add(self) -> None: ...

    @abstractmethod
    def on_delete(self) -> None: ...

    @abstractmethod
    def on_date_changed(self) -> None: ...


class TransactionsView(ABC):
    @abstractmethod
    def set_listener(self, listener: TransactionsListener) -> None: ...

    @abstractmethod
    def set_categories(self, categories: Sequence[str]) -> None: ...

    @abstractmethod
    def get_category(self) -> str: ...

    @abstractmethod
    def set_category(self, name: str) -> None: ...

    @abstractmethod
    def get_form(self) -> TransactionForm: ...

    @abstractmethod
    def get_date_text(self) -> str: ...

    @abstractmethod
    def clear_entry(self) -> None:
        """Vide libellé et montant et redonne le focus au libellé."""

    @abstractmethod
    def show_day(self, title: str, rows: Sequence[Row]) -> None: ...

    @abstractmethod
    def get_selected_ids(self) -> list[str]: ...


# ---------------------------------------------------------------- soldes
class BalanceView(ABC):
    @abstractmethod
    def show_rows(self, rows: Sequence[Row]) -> None: ...


class CategoryDetailListener(ABC):
    @abstractmethod
    def on_filter_changed(self) -> None: ...


class CategoryDetailView(ABC):
    @abstractmethod
    def set_listener(self, listener: CategoryDetailListener) -> None: ...

    @abstractmethod
    def set_filter_options(self, categories: Sequence[str], dates: Sequence[str]) -> None: ...

    @abstractmethod
    def get_filters(self) -> tuple[str, str]: ...

    @abstractmethod
    def set_filters(self, category: str, date: str) -> None: ...

    @abstractmethod
    def show_rows(self, rows: Sequence[Row]) -> None: ...

    @abstractmethod
    def show_totals(self, text: str) -> None: ...


# ---------------------------------------------------------------- catégories
class CategoryManagerListener(ABC):
    @abstractmethod
    def on_add(self) -> None: ...

    @abstractmethod
    def on_rename(self) -> None: ...

    @abstractmethod
    def on_delete(self) -> None: ...


class CategoryManagerView(ABC):
    @abstractmethod
    def set_listener(self, listener: CategoryManagerListener) -> None: ...

    @abstractmethod
    def get_new_name(self) -> str: ...

    @abstractmethod
    def clear_new_name(self) -> None: ...

    @abstractmethod
    def show_categories(self, rows: Sequence[Row]) -> None: ...

    @abstractmethod
    def get_selected_id(self) -> Optional[str]: ...


# ---------------------------------------------------------------- rapport
class ReportListener(ABC):
    @abstractmethod
    def on_generate(self) -> None: ...

    @abstractmethod
    def on_export(self) -> None: ...


class ReportView(ABC):
    @abstractmethod
    def set_listener(self, listener: ReportListener) -> None: ...

    @abstractmethod
    def get_period(self) -> tuple[str, str]: ...

    @abstractmethod
    def set_period(self, start: str, end: str) -> None: ...

    @abstractmethod
    def show_report(self, summary_text: str, rows: Sequence[Row]) -> None: ...

    @abstractmethod
    def reset(self, message: str) -> None: ...


# ---------------------------------------------------------------- budget
class BudgetListener(ABC):
    @abstractmethod
    def on_calculate(self) -> None: ...

    @abstractmethod
    def on_adjust_retained(self, interactive: bool = True) -> None: ...

    @abstractmethod
    def on_change_daily(self) -> None: ...

    @abstractmethod
    def on_validate(self) -> None: ...


class BudgetView(ABC):
    @abstractmethod
    def set_listener(self, listener: BudgetListener) -> None: ...

    @abstractmethod
    def get_period(self) -> tuple[str, str]: ...

    @abstractmethod
    def set_period(self, start: str, end: str) -> None: ...

    @abstractmethod
    def show_proposal(self, summary_text: str, rows: Sequence[Row],
                      selected_id: Optional[str] = None) -> None: ...

    @abstractmethod
    def clear_proposal(self, message: str) -> None: ...

    @abstractmethod
    def get_selected_id(self) -> Optional[str]: ...


# ---------------------------------------------------------------- analyse du budget
class AnalysisListener(ABC):
    @abstractmethod
    def on_analyze(self) -> None: ...

    @abstractmethod
    def on_use_suggestion(self, key: str) -> None: ...

    @abstractmethod
    def on_save_budget(self) -> None: ...

    @abstractmethod
    def on_category_changed(self) -> None: ...

    @abstractmethod
    def on_budget_edited(self) -> None: ...


class AnalysisView(ABC):
    @abstractmethod
    def set_listener(self, listener: AnalysisListener) -> None: ...

    @abstractmethod
    def set_categories(self, categories: Sequence[str]) -> None: ...

    @abstractmethod
    def get_category(self) -> str: ...

    @abstractmethod
    def set_category(self, name: str) -> None: ...

    @abstractmethod
    def get_period(self) -> tuple[str, str]: ...

    @abstractmethod
    def set_period(self, start: str, end: str) -> None: ...

    @abstractmethod
    def show_stats(self, rows: Sequence[Row]) -> None: ...

    @abstractmethod
    def show_suggestions(self, texts: dict) -> None:
        """texts : clé ('serre', 'equilibre', 'confortable') -> montant formaté (ou '—')."""

    @abstractmethod
    def show_diagnostic(self, text: str) -> None: ...

    @abstractmethod
    def get_budget_text(self) -> str: ...

    @abstractmethod
    def set_budget_text(self, text: str) -> None: ...

    @abstractmethod
    def show_current_budget(self, text: str) -> None: ...

    @abstractmethod
    def draw_chart(self, data: Optional[ChartData]) -> None:
        """None = effacer le graphique."""


# ---------------------------------------------------------------- portefeuilles
class WalletsListener(ABC):
    @abstractmethod
    def on_open(self, interactive: bool = True) -> None: ...

    @abstractmethod
    def on_new(self) -> None: ...

    @abstractmethod
    def on_link_file(self) -> None: ...

    @abstractmethod
    def on_rename(self) -> None: ...

    @abstractmethod
    def on_remove(self) -> None: ...


class WalletsView(ABC):
    @abstractmethod
    def set_listener(self, listener: WalletsListener) -> None: ...

    @abstractmethod
    def show_wallets(self, rows: Sequence[Row], total_text: str) -> None: ...

    @abstractmethod
    def get_selected_id(self) -> Optional[str]: ...


# ---------------------------------------------------------------- fabrique abstraite
# ---------------------------------------------------------------- authentification
class AuthListener(ABC):
    @abstractmethod
    def on_submit(self) -> None:
        """Valider le formulaire affiché (connexion, création de compte ou réinitialisation)."""

    @abstractmethod
    def on_switch_mode(self, mode: AuthMode) -> None: ...

    @abstractmethod
    def on_privacy(self) -> None: ...

    @abstractmethod
    def on_help(self) -> None: ...


class AuthView(ABC):
    @abstractmethod
    def set_listener(self, listener: AuthListener) -> None: ...

    @abstractmethod
    def show_mode(self, mode: AuthMode, greeting: str, email: str = "") -> None:
        """Affiche le formulaire du mode demandé (et efface les erreurs et les mots de passe saisis)."""

    @abstractmethod
    def get_form(self) -> AuthForm: ...

    @abstractmethod
    def show_error(self, message: str) -> None: ...

    @abstractmethod
    def clear_secrets(self) -> None: ...


class AccountListener(ABC):
    @abstractmethod
    def on_logout(self) -> None: ...


class AccountView(ABC):
    @abstractmethod
    def set_listener(self, listener: AccountListener) -> None: ...

    @abstractmethod
    def show_user(self, name: str, email: str) -> None: ...


class Screens(ABC):
    """Bascule entre l'écran d'authentification et l'application."""

    @abstractmethod
    def show_login(self) -> None: ...

    @abstractmethod
    def show_app(self) -> None: ...


# ---------------------------------------------------------------- tableau de bord
class DashboardListener(ABC):
    @abstractmethod
    def on_apply_filter(self) -> None:
        """Appliquer la période saisie au graphique des entrées et sorties."""

    @abstractmethod
    def on_preset(self, days: Optional[int]) -> None:
        """Raccourci de période : les `days` derniers jours de données, ou toute la période si None."""


class DashboardView(ABC):
    @abstractmethod
    def set_listener(self, listener: DashboardListener) -> None: ...

    @abstractmethod
    def get_period(self) -> tuple[str, str]: ...

    @abstractmethod
    def set_period(self, start: str, end: str) -> None: ...

    @abstractmethod
    def show_budget_shares(self, data: Optional[PieData]) -> None: ...

    @abstractmethod
    def show_flows(self, data: Optional[FlowChartData]) -> None: ...


# ---------------------------------------------------------------- synchronisation
class SyncListener(ABC):
    @abstractmethod
    def on_send(self) -> None:
        """Envoyer les données du PC aux appareils connectés, à partir de la date saisie."""

    @abstractmethod
    def on_fetch(self) -> None:
        """Demander aux appareils connectés d'envoyer leurs données."""

    @abstractmethod
    def on_device_connected(self, client: int, address: str) -> None: ...

    @abstractmethod
    def on_device_disconnected(self, client: int, address: str) -> None: ...

    @abstractmethod
    def on_message(self, client: int, address: str, text: str) -> None:
        """Un appareil a envoyé ce message (texte JSON, voir adapters/driving/sync_protocol.py)."""


class SyncView(ABC):
    """Onglet de synchronisation. La vue possède le serveur réseau et transmet ses événements au contrôleur,
    DANS le thread de l'interface (le contrôleur n'a donc jamais à se soucier des threads)."""

    @abstractmethod
    def set_listener(self, listener: SyncListener) -> None: ...

    @abstractmethod
    def start_date_text(self) -> str:
        """Date de début saisie (JJ/MM/AAAA) ; vide = tout l'historique."""

    @abstractmethod
    def device_count(self) -> int: ...

    @abstractmethod
    def send(self, text: str, client: Optional[int] = None) -> int:
        """Envoie un message à un appareil (tous si `client` est None) ; retourne le nombre d'appareils atteints."""

    @abstractmethod
    def confirm_transfer(self, title: str, heading: str, notes: Sequence[str], rows: Sequence[Row],
                         confirm_label: str) -> bool:
        """Fenêtre modale : liste des données (colonnes : portefeuille, date, catégorie, libellé, montant) et
        boutons Annuler / `confirm_label`. Retourne True seulement si l'utilisateur confirme."""

    @abstractmethod
    def show_message(self, line: str) -> None:
        """Ajoute une ligne à la zone de journal affichée."""

    @abstractmethod
    def show_journal(self, lines: Sequence[str], location: str) -> None: ...


class UserInterface(ABC):
    """Regroupe toutes les vues d'une bibliothèque graphique (fabrique abstraite).

    Une implémentation par bibliothèque : TkUserInterface (tkinter), un jour CtkUserInterface
    (customtkinter). `bootstrap.py` ne dépend que de cette interface.
    """
    header: HeaderView
    dashboard: DashboardView
    transactions: TransactionsView
    balances: BalanceView
    category_details: CategoryDetailView
    categories: CategoryManagerView
    report: ReportView
    budget: BudgetView
    analysis: AnalysisView
    wallets: WalletsView
    dialogs: Dialogs
    navigator: Navigator
    # facultatifs : une interface sans authentification les laisse à None (l'application démarre directement)
    auth: Optional[AuthView] = None
    account: Optional[AccountView] = None
    screens: Optional[Screens] = None
    sync: Optional[SyncView] = None   # facultatif : sans lui (ou sans journal), l'onglet reste autonome

    @abstractmethod
    def run(self) -> None:
        """Affiche la fenêtre et démarre la boucle d'événements."""
