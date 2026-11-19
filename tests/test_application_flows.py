"""Parcours complets : contrôleurs (vues simulées) -> cas d'usage -> domaine -> adaptateurs EN MÉMOIRE.

Aucun fichier, aucune fenêtre : la preuve que le cœur de l'application ne dépend d'aucun adaptateur.
"""
import datetime as dt
import unittest

from suivi.adapters.driving.gui.contract.dto import TransactionForm
from suivi.application.errors import StorageError
from suivi.application.use_cases.transactions import TransactionsUseCase  # noqa: F401
from suivi.bootstrap import build_application
from suivi.domain.model.transaction import Kind, Transaction

from .fakes import make_ports, make_ui


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.ports, self.ui = make_ports(), make_ui()
        self.app = build_application(self.ui, self.ports, "/export")
        self.app.start()

    def stored(self, location="principal"):
        return self.ports.ledgers.stored[location]

    def add_category(self, name):
        self.ui.categories.get_new_name.return_value = name
        self.ui.categories.set_listener.call_args[0][0].on_add()

    def add_transaction(self, date, category, kind, label, amount):
        self.ui.transactions.get_form.return_value = TransactionForm(date, category, kind, label, amount)
        self.ui.transactions.set_listener.call_args[0][0].on_add()

    def listener(self, view):
        return view.set_listener.call_args[0][0]

    # ---- saisie ------------------------------------------------------------------------------------
    def test_ajouter_categorie_et_transactions(self):
        self.add_category("bazar")
        self.add_transaction("01/09/2026", "bazar", "dépôt", "", "10 000 Ar")
        self.add_transaction("01/09/2026", "bazar", "dépense", "riz", "3 200")
        ledger = self.stored()
        self.assertEqual(ledger.categories, ["bazar"])
        self.assertEqual([t.amount for t in ledger.transactions], [10000, 3200])
        self.assertEqual(ledger.transactions[0].label, "dépôt")        # libellé par défaut d'un dépôt
        title = self.ui.transactions.show_day.call_args[0][0]
        self.assertIn("6 800 Ar", title)                               # solde à la date affichée

    def test_saisie_invalide_donne_un_avertissement_sans_rien_enregistrer(self):
        self.add_category("bazar")
        self.add_transaction("01/09/2026", "bazar", "dépense", "riz", "0")
        self.add_transaction("pas une date", "bazar", "dépense", "riz", "100")
        self.assertEqual(self.ui.dialogs.warning.call_count, 2)
        self.assertEqual(len(self.stored().transactions), 0)

    def test_sans_categorie_on_est_renvoye_vers_l_onglet_categories(self):
        self.add_transaction("01/09/2026", "", "dépense", "riz", "100")
        self.ui.navigator.show_tab.assert_called()
        self.assertNotIn("principal", self.ports.ledgers.stored)          # rien n'a été enregistré

    def test_supprimer(self):
        self.add_category("bazar")
        self.add_transaction("01/09/2026", "bazar", "dépense", "riz", "100")
        self.add_transaction("01/09/2026", "bazar", "dépense", "pain", "200")
        self.ui.transactions.get_selected_ids.return_value = ["0"]
        self.listener(self.ui.transactions).on_delete()
        self.assertEqual([t.label for t in self.stored().transactions], ["pain"])

    # ---- échec de stockage -----------------------------------------------------------------------------
    def test_echec_d_ecriture_ne_modifie_rien_et_previent_l_utilisateur(self):
        self.add_category("bazar")
        self.ports.ledgers.fail_on_save = StorageError("Fichier verrouillé", locked=True)
        self.add_transaction("01/09/2026", "bazar", "dépense", "riz", "100")
        self.ui.dialogs.error.assert_called_with("Fichier verrouillé", "Fichier verrouillé")
        self.ports.ledgers.fail_on_save = None
        self.ui.transactions.show_day.reset_mock()
        self.listener(self.ui.transactions).on_date_changed()
        self.assertEqual(self.ui.transactions.show_day.call_args[0][1], [])   # rien en mémoire non plus

    # ---- catégories --------------------------------------------------------------------------------------
    def test_renommer_et_supprimer_categorie(self):
        self.add_category("bazar")
        self.add_category("riz")
        self.add_transaction("01/09/2026", "bazar", "dépense", "x", "100")
        listener = self.listener(self.ui.categories)
        self.ui.categories.get_selected_id.return_value = "0"            # « bazar » (triées)
        self.ui.dialogs.ask_text.return_value = "marché"
        listener.on_rename()
        self.assertEqual(self.stored().transactions[0].category, "marché")
        self.ui.categories.get_selected_id.return_value = "0"            # « marché » est utilisée
        listener.on_delete()
        self.ui.dialogs.warning.assert_called()
        self.ui.categories.get_selected_id.return_value = "1"            # « riz » est libre (triées : marché, riz)
        listener.on_delete()
        self.assertEqual(self.stored().categories, ["marché"])

    # ---- budget ------------------------------------------------------------------------------------------------
    def test_budget_suggestion_ajustement_et_depots(self):
        self.add_category("gouter")
        self.add_transaction("30/09/2026", "gouter", "dépôt", "", "3000")
        self.add_transaction("30/09/2026", "gouter", "dépense", "x", "2000")
        self.listener(self.ui.categories)   # (contrôleur existant)
        # budget par jour via l'onglet Budget
        self.ui.budget.get_period.return_value = ("01/10/2026", "07/10/2026")
        budget = self.listener(self.ui.budget)
        budget.on_calculate()
        self.ui.budget.get_selected_id.return_value = "0"
        self.ui.dialogs.ask_int.return_value = 500
        budget.on_change_daily()                                         # définit 500 Ar/jour puis recalcule
        self.assertEqual(self.stored().budgets, {"gouter": 500})
        rows = self.ui.budget.show_proposal.call_args[0][1]
        self.assertEqual(rows[0].values[4:], ("2 500 Ar", "2 500 Ar"))   # suggestion = retenu = 2 500
        self.ui.dialogs.ask_int.return_value = 3000                      # l'utilisateur ajuste à 3 000
        budget.on_adjust_retained()
        budget.on_validate()
        deposit = self.stored().transactions[-1]
        self.assertEqual((deposit.kind, deposit.amount, deposit.date), (Kind.DEPOSIT, 3000, dt.date(2026, 10, 1)))
        self.assertEqual(deposit.label, "Budget du 01/10/2026 au 07/10/2026")

    def test_budget_deja_valide_demande_confirmation(self):
        self.add_category("gouter")
        self.ui.budget.get_period.return_value = ("01/10/2026", "03/10/2026")
        self.ui.budget.get_selected_id.return_value = "0"
        budget = self.listener(self.ui.budget)
        self.ui.dialogs.ask_int.return_value = 100
        budget.on_calculate()
        budget.on_change_daily()
        budget.on_validate()
        self.ui.dialogs.confirm.reset_mock()
        self.ui.dialogs.confirm.return_value = False                     # on refuse le doublon
        budget.on_calculate()
        budget.on_validate()
        self.assertEqual(len([t for t in self.stored().transactions if t.kind is Kind.DEPOSIT]), 1)

    # ---- analyse --------------------------------------------------------------------------------------------------
    def test_analyse_puis_enregistrement_du_budget_par_jour(self):
        self.add_category("bazar")
        self.add_transaction("01/09/2026", "bazar", "dépense", "x", "3000")
        self.add_transaction("03/09/2026", "bazar", "dépense", "x", "1000")
        self.ui.analysis.get_category.return_value = "bazar"
        self.ui.analysis.get_period.return_value = ("01/09/2026", "03/09/2026")
        analysis = self.listener(self.ui.analysis)
        analysis.on_analyze()
        chart = self.ui.analysis.draw_chart.call_args[0][0]
        self.assertEqual(chart.values, [3000, 0, 1000])
        self.ui.analysis.set_budget_text.assert_called_with("1300")      # moyenne proposée par défaut
        self.ui.analysis.get_budget_text.return_value = "1300"
        analysis.on_save_budget()
        self.assertEqual(self.stored().budgets, {"bazar": 1300})

    # ---- rapport -----------------------------------------------------------------------------------------------------
    def test_rapport_et_export(self):
        self.add_category("bazar")
        self.add_transaction("01/09/2026", "bazar", "dépense", "x", "1000")
        self.ui.report.get_period.return_value = ("01/09/2026", "02/09/2026")
        self.ui.dialogs.ask_save_file.return_value = "/export/r.txt"
        report = self.listener(self.ui.report)
        report.on_export()
        self.assertEqual(self.ports.exporter.exported[0][1], "/export/r.txt")
        name = self.ui.dialogs.ask_save_file.call_args[0][2]
        self.assertEqual(name, "rapport_principal_20260901_20260902.txt")   # extension fournie par l'adaptateur
        self.assertEqual(self.ports.opener.opened, ["/export/r.txt"])

    # ---- import --------------------------------------------------------------------------------------------------------------
    def test_import_cree_les_categories(self):
        self.ports.importer.transactions = [Transaction(dt.date(2026, 9, 5), "riz", Kind.EXPENSE, "x", 500)]
        self.ui.dialogs.ask_open_file.return_value = "/tmp/in.mem"
        self.listener(self.ui.header).on_import()
        self.assertEqual(self.stored().categories, ["riz"])
        self.assertEqual(self.ui.dialogs.ask_open_file.call_args[0][1], ("*.mem",))   # types fournis par le port

    # ---- portefeuilles -----------------------------------------------------------------------------------------------------
    def test_portefeuilles_creer_changer_renommer_retirer(self):
        self.add_category("bazar")
        wallets = self.listener(self.ui.wallets)
        self.ui.dialogs.ask_text.return_value = "Banque"
        wallets.on_new()
        self.assertEqual(self.app.wallets.active_name(), "Banque")
        self.assertEqual(self.stored("banque").categories, [])           # portefeuille vide et séparé
        self.assertEqual(self.ports.registry.catalog.active, "Banque")   # le choix est mémorisé
        self.listener(self.ui.header).on_wallet_selected("Principal")
        self.assertEqual(self.ui.header.show_wallets.call_args[0], (["Principal", "Banque"], "Principal"))
        self.ui.wallets.get_selected_id.return_value = "1"               # « Banque »
        self.ui.dialogs.ask_text.return_value = "Caisse"
        wallets.on_rename()
        self.assertEqual(self.app.wallets.names(), ["Principal", "Caisse"])
        wallets.on_remove()
        self.assertEqual(self.app.wallets.names(), ["Principal"])
        self.assertIn("banque", self.ports.ledgers.stored)               # le stockage n'est jamais supprimé
        self.ui.wallets.get_selected_id.return_value = "0"
        wallets.on_remove()                                              # le dernier ne peut pas être retiré
        self.assertEqual(self.app.wallets.names(), ["Principal"])

    def test_ouvrir_le_stockage_sans_fichier_previent(self):
        self.listener(self.ui.header).on_open_storage()
        self.ui.dialogs.warning.assert_called()


if __name__ == "__main__":
    unittest.main()
