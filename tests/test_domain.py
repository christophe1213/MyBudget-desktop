"""Le domaine seul : aucune interface, aucun stockage, aucune bibliothèque tierce."""
import datetime as dt
import unittest

from suivi.domain.model.errors import DomainError
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.period import Period
from suivi.domain.model.transaction import Kind
from suivi.domain.model.wallet import WalletCatalog, WalletRef
from suivi.domain.services.balances import BalanceCalculator
from suivi.domain.services.budget import BudgetPlanner
from suivi.domain.services.reports import ReportBuilder
from suivi.domain.services.spending import SpendingAnalyzer

D = dt.date


def sample() -> Ledger:
    ledger = Ledger(initial_balance=1000, categories=["bazar", "gouter"])
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.DEPOSIT, "", 10000)
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.EXPENSE, "riz", 3000)
    ledger.add_transaction(D(2026, 9, 3), "bazar", Kind.EXPENSE, "riz", 1000)
    ledger.add_transaction(D(2026, 9, 3), "gouter", Kind.EXPENSE, "wifi", 500)
    return ledger


class LedgerTest(unittest.TestCase):
    def test_categories_unique_sans_casse_et_triees(self):
        ledger = Ledger(categories=["riz"])
        ledger.add_category("Bazar")
        with self.assertRaises(DomainError):
            ledger.add_category("BAZAR")
        self.assertEqual(ledger.categories, ["Bazar", "riz"])

    def test_transaction_exige_categorie_connue_et_montant_positif(self):
        ledger = Ledger(categories=["riz"])
        with self.assertRaises(DomainError):
            ledger.add_transaction(D(2026, 9, 1), "inconnue", Kind.EXPENSE, "", 100)
        with self.assertRaises(DomainError):
            ledger.add_transaction(D(2026, 9, 1), "riz", Kind.EXPENSE, "", 0)

    def test_renommer_deplace_transactions_et_budget(self):
        ledger = sample()
        ledger.set_daily_budget("bazar", 3700)
        ledger.rename_category("bazar", "marché")
        self.assertEqual({t.category for t in ledger.transactions}, {"marché", "gouter"})
        self.assertEqual(ledger.budgets, {"marché": 3700})

    def test_supprimer_categorie_utilisee_est_refusee(self):
        with self.assertRaises(DomainError):
            sample().remove_category("bazar")

    def test_copie_independante(self):
        ledger = sample()
        copy = ledger.copy()
        copy.add_category("neuf")
        copy.remove_transactions([0])
        self.assertEqual(len(ledger.transactions), 4)
        self.assertNotIn("neuf", ledger.categories)

    def test_import_cree_les_categories_manquantes(self):
        other = sample()
        target = Ledger()
        self.assertEqual(sorted(target.new_categories_in(other.transactions)), ["bazar", "gouter"])
        target.merge(other.transactions)
        self.assertEqual(target.categories, ["bazar", "gouter"])


class ServicesTest(unittest.TestCase):
    def test_soldes(self):
        ledger, calc = sample(), BalanceCalculator()
        self.assertEqual([r.balance for r in calc.by_date(ledger)], [8000, 6500])
        self.assertEqual(calc.at(ledger, D(2026, 9, 2)), 8000)
        self.assertEqual(calc.at(ledger, D(2026, 8, 1)), 1000)
        self.assertEqual(calc.total(ledger), 6500)
        by_category = {(r.date, r.category): r.balance for r in calc.by_category(ledger)}
        self.assertEqual(by_category[(D(2026, 9, 3), "bazar")], 6000)

    def test_rapport(self):
        report = ReportBuilder().build(sample(), Period(D(2026, 9, 2), D(2026, 9, 3)))
        self.assertEqual((report.opening_balance, report.closing_balance), (8000, 6500))
        self.assertEqual((report.total_deposits, report.total_expenses, report.transaction_count), (0, 1500, 2))
        self.assertEqual([c.category for c in report.categories], ["bazar", "gouter"])
        self.assertEqual(report.categories[0].expense_share, 66.7)
        self.assertEqual(report.average_daily_expense, 750)

    def test_budget_exemple_de_l_utilisateur(self):
        """gouter 500 Ar/jour, 1 000 Ar restants, 7 jours -> 7x500 - 1000 = 2 500."""
        ledger = Ledger(categories=["gouter"])
        ledger.add_transaction(D(2026, 9, 30), "gouter", Kind.DEPOSIT, "", 3000)
        ledger.add_transaction(D(2026, 9, 30), "gouter", Kind.EXPENSE, "", 2000)
        ledger.set_daily_budget("gouter", 500)
        line = BudgetPlanner().propose(ledger, Period(D(2026, 10, 1), D(2026, 10, 7)))[0]
        self.assertEqual((line.needed, line.balance, line.suggestion), (3500, 1000, 2500))

    def test_budget_jamais_negatif(self):
        ledger = Ledger(categories=["riz"])
        ledger.add_transaction(D(2026, 9, 30), "riz", Kind.DEPOSIT, "", 99999)
        ledger.set_daily_budget("riz", 100)
        self.assertEqual(BudgetPlanner().propose(ledger, Period(D(2026, 10, 1), D(2026, 10, 3)))[0].suggestion, 0)

    def test_analyse_compte_les_jours_sans_depense(self):
        analysis = SpendingAnalyzer().analyze(sample(), "bazar", Period(D(2026, 9, 1), D(2026, 9, 3)))
        self.assertEqual([v for _d, v in analysis.daily], [3000, 0, 1000])
        self.assertEqual(analysis.stats.suggestions["serre"], 1300)
        self.assertEqual(analysis.stats.days_with_expense, 2)

    def test_periode_inversee_refusee(self):
        with self.assertRaises(DomainError):
            Period(D(2026, 9, 3), D(2026, 9, 1))


class CatalogTest(unittest.TestCase):
    def test_regles(self):
        catalog = WalletCatalog((WalletRef("Principal", "a"),), "Principal")
        with self.assertRaises(DomainError):
            catalog.with_wallet(WalletRef("principal", "b"))      # même nom (casse ignorée)
        with self.assertRaises(DomainError):
            catalog.without("Principal")                          # dernier portefeuille
        two = catalog.with_wallet(WalletRef("Banque", "b"), make_active=True)
        self.assertEqual(two.active, "Banque")
        self.assertEqual(two.without("Banque").active, "Principal")
        self.assertEqual(two.renamed("Banque", "Caisse").active, "Caisse")


if __name__ == "__main__":
    unittest.main()
