"""Maquette de la page « Transactions » (customtkinter) : l'onglet existe, « Saisie » est conservée, les écrans
s'enchaînent. Les bibliothèques graphiques sont simulées (comme dans test_tk_views_smoke) : aucune fenêtre."""
import importlib
import sys
import unittest
from unittest.mock import patch

from suivi.adapters.driving.gui.contract.dto import Tab
from tests.test_tk_views_smoke import INTERFACES, fake_gui_modules, forget_gui_modules


def build(interface: str):
    module_name, class_name = INTERFACES[interface]
    return importlib.import_module(module_name), getattr(importlib.import_module(module_name), class_name)("Test")


class TransactionsPageTest(unittest.TestCase):
    def test_onglet_apres_saisie_et_saisie_conservee(self):
        with patch.dict(sys.modules, fake_gui_modules()):
            forget_gui_modules()
            module, ui = build("ctk")
            order = list(module._PAGES)
            self.assertIn(Tab.ENTRY, order)                                        # « Saisie » est toujours là
            self.assertEqual(order.index(Tab.TRANSACTIONS), order.index(Tab.ENTRY) + 1)
            self.assertEqual(module._PAGES[Tab.TRANSACTIONS][0], "Transactions")
            ui.navigator.show_tab(Tab.TRANSACTIONS)
            ui.navigator.show_tab(Tab.ENTRY)
        forget_gui_modules()

    def test_parcours_de_la_maquette(self):
        with patch.dict(sys.modules, fake_gui_modules()):
            forget_gui_modules()
            _module, ui = build("ctk")
            page = ui.transactions_page
            self.assertEqual(page.current, "list")
            self.assertEqual(set(page._screens), {"list", "choice", "expense", "deposit", "transfer", "review"})
            for name in page._screens:
                page._show(name)
                self.assertEqual(page.current, name)
            page._todo()                                                           # emplacement vide : ne fait rien
        forget_gui_modules()

    def test_interface_classique_inchangee(self):
        """L'interface tkinter classique n'a pas l'onglet maquette et se construit comme avant."""
        with patch.dict(sys.modules, fake_gui_modules()):
            forget_gui_modules()
            _module, ui = build("tk")
            self.assertFalse(hasattr(ui, "transactions_page"))
        forget_gui_modules()


if __name__ == "__main__":
    unittest.main()
