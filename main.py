"""Point d'entrée.

    python main.py                       interface customtkinter (vert Excel), connexion obligatoire,
                                         données dans des classeurs Excel, comptes dans comptes.db (SQLModel)
    python main.py --classic             interface tkinter classique (sans connexion)
    python main.py --sqlite              données financières dans SQLite (suivi.db) au lieu des classeurs Excel
    python main.py --no-auth             démarrer sans écran de connexion (développement)

Les options se combinent (ex. python main.py --sqlite --no-auth).
Pour une autre interface ou un autre stockage : voir README.md.
"""
import os
import sys

from suivi.adapters.driven.auth_wiring import sqlmodel_auth_ports
from suivi.adapters.driven.sync_journal import TextSyncJournal
from suivi.adapters.driven.wiring import excel_ports, sqlite_ports
from suivi.bootstrap import build_application

APP_TITLE = "Repère"


def data_dir() -> str:
    """Dossier des données : à côté du .exe une fois compilé, sinon à côté de main.py."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def create_user_interface():
    """Choix de l'adaptateur d'interface (importé à la demande : chaque bibliothèque reste facultative)."""
    if "--classic" in sys.argv:
        from suivi.adapters.driving.gui.tk.user_interface import TkUserInterface
        return TkUserInterface(APP_TITLE)
    from suivi.adapters.driving.gui.ctk.user_interface import CtkUserInterface
    return CtkUserInterface(APP_TITLE)


def main() -> None:
    folder = data_dir()
    ports = sqlite_ports(folder) if "--sqlite" in sys.argv else excel_ports(folder)
    with_auth = "--no-auth" not in sys.argv and "--classic" not in sys.argv   # l'interface classique n'a pas d'écran de connexion
    auth_ports = sqlmodel_auth_ports(folder) if with_auth else None
    journal = TextSyncJournal(os.path.join(folder, "journal_synchronisation.txt"))
    build_application(create_user_interface(), ports, folder, APP_TITLE, auth_ports, journal).run()


if __name__ == "__main__":
    main()
