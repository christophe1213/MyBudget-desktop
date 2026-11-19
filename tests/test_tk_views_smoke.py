"""Test de fumée des vues (tkinter classique ET customtkinter) SANS écran : les bibliothèques sont simulées.

Il vérifie que chaque interface implémente tous les contrats de vues (classes abstraites), que
l'application s'assemble avec chaque stockage, et qu'un parcours complet va de la vue jusqu'au stockage.
Il ne vérifie PAS l'apparence : pour cela, lancer main.py.
"""
import importlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from suivi.adapters.driven.auth_wiring import sqlmodel_auth_ports
from suivi.adapters.driven.wiring import excel_ports, sqlite_ports
from suivi.adapters.driving.gui.contract.dto import ChartData
from suivi.adapters.driving.gui.contract.interfaces import Dialogs
from suivi.bootstrap import build_application
from suivi.domain.model.transaction import Kind


class FakeStringVar:
    def __init__(self, value=""):
        self._value, self._traces = value, []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for callback in list(self._traces):
            callback()

    def trace_add(self, _mode, callback):
        self._traces.append(lambda: callback())


def fake_gui_modules():
    tk, ctk = MagicMock(), MagicMock()
    tk.StringVar = ctk.StringVar = ctk.BooleanVar = FakeStringVar
    canvas = MagicMock()                       # les graphiques se dessinent vraiment sur ce canevas simulé
    canvas.winfo_width.return_value, canvas.winfo_height.return_value = 900, 300
    canvas.bbox.return_value = (0, 0, 60, 10)
    tk.Canvas = MagicMock(return_value=canvas)
    return {"tkinter": tk, "tkinter.ttk": MagicMock(), "tkinter.messagebox": MagicMock(),
            "tkinter.filedialog": MagicMock(), "tkinter.simpledialog": MagicMock(), "customtkinter": ctk}


INTERFACES = {"tk": ("suivi.adapters.driving.gui.tk.user_interface", "TkUserInterface"),
              "ctk": ("suivi.adapters.driving.gui.ctk.user_interface", "CtkUserInterface")}


def forget_gui_modules():
    for name in [m for m in sys.modules if m.startswith(("suivi.adapters.driving.gui.tk",
                                                         "suivi.adapters.driving.gui.ctk"))]:
        del sys.modules[name]


class TkViewsSmokeTest(unittest.TestCase):
    def run_scenario(self, interface, make_ports, location):
        folder = tempfile.mkdtemp()
        module_name, class_name = INTERFACES[interface]
        with patch.dict(sys.modules, fake_gui_modules()):
            forget_gui_modules()
            ui = getattr(importlib.import_module(module_name), class_name)("Test")
            dialogs = MagicMock(spec=Dialogs)
            dialogs.confirm.return_value = True
            ui.dialogs = dialogs      # dialogues scénarisées (pas de vraie fenêtre)
            ports = make_ports(folder)
            app = build_application(ui, ports, folder, "Test")
            app.start()
            self.scenario(ui, dialogs, ports, location, app)
        forget_gui_modules()

    def scenario(self, ui, dialogs, ports, location, app):
        stored = lambda loc=location: ports.ledgers.load(loc)  # noqa: E731

        for name in ("bazar", "gouter"):      # catégories (onglet Catégories)
            ui.categories._new_name.set(name)
            ui.categories._listener.on_add()
        self.assertEqual(stored().categories, ["bazar", "gouter"])
        self.assertEqual(ui.categories._new_name.get(), "")

        def add(date, category, kind, label, amount):
            t = ui.transactions
            t._date.set(date), t._category.set(category), t._kind.set(kind)
            t._label.set(label), t._amount.set(amount)
            t._listener.on_add()

        add("01/09/2026", "bazar", "dépôt", "", "10 000 Ar")
        for day, amount in [("01/09/2026", "3 000"), ("02/09/2026", "0"), ("03/09/2026", "1 000")]:
            add(day, "bazar", "dépense", "tomates", amount)
        self.assertEqual(len(stored().transactions), 3)       # le montant 0 a été refusé
        dialogs.warning.assert_called()

        drawn = []                                             # analyse : le graphique reçoit des données
        ui.analysis._chart.draw = lambda data: drawn.append(data)
        ui.analysis._category.set("bazar")
        ui.analysis._start.set("01/09/2026"), ui.analysis._end.set("03/09/2026")
        ui.analysis._listener.on_analyze()
        self.assertIsInstance(drawn[-1], ChartData)
        self.assertEqual(drawn[-1].values, [3000, 0, 1000])
        ui.analysis._listener.on_save_budget()                # budget = moyenne (1 300 Ar)
        self.assertEqual(stored().budgets["bazar"], 1300)

        ui.budget._start.set("10/09/2026"), ui.budget._end.set("16/09/2026")   # budget sur 7 jours
        ui.budget._listener.on_calculate()
        ui.budget._listener.on_validate()
        deposits = [t for t in stored().transactions if t.label.startswith("Budget du")]
        self.assertEqual(sum(t.amount for t in deposits), 1300 * 7 - 6000)
        self.assertTrue(all(t.kind is Kind.DEPOSIT for t in deposits))

        dialogs.ask_text.return_value = "Caisse"              # portefeuilles
        ui.wallets._listener.on_new()
        self.assertEqual(ui.header._wallet.get(), "Caisse")
        ui.header._listener.on_wallet_selected("Principal")
        self.assertEqual(len(stored().transactions), 4)
        self.assertEqual(app.wallets.names(), ["Principal", "Caisse"])

    def build_ctk(self, folder, with_auth, interface="ctk"):
        module_name, class_name = INTERFACES[interface]
        ui = getattr(importlib.import_module(module_name), class_name)("Repère")
        dialogs = MagicMock(spec=Dialogs)
        dialogs.confirm.return_value = True
        ui.dialogs = dialogs
        auth_ports = sqlmodel_auth_ports(folder) if with_auth else None
        return ui, dialogs, build_application(ui, excel_ports(folder), folder, "Repère", auth_ports)

    def test_authentification_de_bout_en_bout_avec_le_vrai_sqlmodel(self):
        import os
        folder = tempfile.mkdtemp()
        with patch.dict(sys.modules, fake_gui_modules()):
            forget_gui_modules()
            ui, dialogs, app = self.build_ctk(folder, with_auth=True)
            app.start()
            # écran de connexion affiché, données NON chargées tant qu'on n'est pas connecté
            self.assertFalse(os.path.exists(os.path.join(folder, "portefeuilles.txt")))
            self.assertIsNotNone(app.auth_controller)
            form = ui.auth
            # premier lancement : création du compte
            form._name.set("Rina Laurent"), form._email.set("rina@exemple.fr")
            form._password.set("motdepasse1"), form._confirmation.set("motdepasse1")
            form._listener.on_submit()
            self.assertIn("clé de récupération", dialogs.info.call_args[0][0].lower())
            self.assertTrue(os.path.exists(os.path.join(folder, "portefeuilles.txt")))   # application démarrée
            ui.account._name.configure.assert_any_call(text="Rina Laurent")
            # déconnexion puis reconnexion avec « Rester connecté·e »
            ui.account._listener.on_logout()
            form._email.set("rina@exemple.fr"), form._password.set("motdepasse1"), form._remember.set(True)
            form._listener.on_submit()
            with open(os.path.join(folder, "session.json"), encoding="utf-8") as f:
                self.assertIn("rina@exemple.fr", f.read())
            # nouveau lancement : reconnexion automatique, sans écran de connexion
            ui2, _d2, app2 = self.build_ctk(folder, with_auth=True)
            app2.start()
            self.assertTrue(app2._main_started)           # connecté d'office : l'application est déjà ouverte
            ui2.account._name.configure.assert_any_call(text="Rina Laurent")
        forget_gui_modules()

    def test_interface_classique_demarre_sans_connexion_meme_si_les_comptes_sont_fournis(self):
        folder = tempfile.mkdtemp()
        with patch.dict(sys.modules, fake_gui_modules()):
            forget_gui_modules()
            ui, _dialogs, app = self.build_ctk(folder, with_auth=True, interface="tk")
            self.assertIsNone(app.auth_controller)
            app.start()
        forget_gui_modules()

    def test_toutes_les_combinaisons_interface_et_stockage(self):
        for interface in INTERFACES:
            for make_ports, location in ((excel_ports, "transactions.xlsx"), (sqlite_ports, "principal")):
                with self.subTest(interface=interface, stockage=make_ports.__name__):
                    self.run_scenario(interface, make_ports, location)


if __name__ == "__main__":
    unittest.main()
