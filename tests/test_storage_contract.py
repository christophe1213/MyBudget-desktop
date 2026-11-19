"""Tests de CONTRAT des adaptateurs de stockage : les mêmes exigences pour Excel et pour SQLite.

Un futur adaptateur (sqlmodel, PostgreSQL...) doit passer exactement ces tests pour être branché.
"""
import datetime as dt
import os
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import Workbook

from suivi.adapters.driven.excel.importer import ExcelTransactionImporter
from suivi.adapters.driven.wiring import excel_ports, sqlite_ports
from suivi.application.errors import StorageError
from suivi.domain.model.errors import DomainError
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.transaction import Kind
from suivi.domain.model.wallet import WalletCatalog, WalletRef

D = dt.date


def sample_ledger() -> Ledger:
    ledger = Ledger(initial_balance=16600, categories=["bazar", "gouter", "inutilisée"])
    ledger.add_transaction(D(2026, 9, 2), "bazar", Kind.DEPOSIT, "", 52700)
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.EXPENSE, "œuf et pâtes", 900)
    ledger.add_transaction(D(2026, 9, 1), "gouter", Kind.EXPENSE, "wifi", 500)
    ledger.set_daily_budget("bazar", 3700)
    return ledger


class StorageContract:
    """À mélanger avec unittest.TestCase ; la sous-classe fournit `make_ports`."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.ports = self.make_ports(self.folder)

    def loc(self, name):
        """Un emplacement valide pour ce stockage (les emplacements viennent toujours de la politique)."""
        return self.ports.locations.suggest_location(name, [])

    def test_aller_retour_complet(self):
        where = self.loc("w1")
        self.ports.ledgers.save(where, sample_ledger())
        back = self.ports.ledgers.load(where)
        self.assertEqual(sorted(back.transactions, key=lambda t: (t.date, t.label)),
                         sorted(sample_ledger().transactions, key=lambda t: (t.date, t.label)))
        self.assertEqual((back.initial_balance, back.budgets), (16600, {"bazar": 3700}))
        self.assertEqual(back.categories, ["bazar", "gouter", "inutilisée"])   # catégorie sans transaction conservée

    def test_emplacement_absent_donne_un_livre_vide(self):
        where = self.loc("nouveau")
        self.assertFalse(self.ports.ledgers.exists(where))
        self.assertEqual(self.ports.ledgers.load(where).transactions, ())
        self.ports.ledgers.save(where, Ledger())
        self.assertTrue(self.ports.ledgers.exists(where))

    def test_les_portefeuilles_sont_isoles_et_reecrire_remplace(self):
        a, b = self.loc("a"), self.loc("b")
        self.ports.ledgers.save(a, sample_ledger())
        self.ports.ledgers.save(b, Ledger(categories=["x"]))
        smaller = sample_ledger()
        smaller.remove_transactions([0, 1])
        self.ports.ledgers.save(a, smaller)
        self.assertEqual(len(self.ports.ledgers.load(a).transactions), 1)
        self.assertEqual(self.ports.ledgers.load(b).categories, ["x"])

    def test_registre(self):
        default = self.ports.registry.load()
        self.assertEqual(len(default.wallets), 1)
        catalog = WalletCatalog((WalletRef("Principal", "p"), WalletRef("Épargne; #1", "e")), "Épargne; #1")
        self.ports.registry.save(catalog)
        self.assertEqual(self.ports.registry.load(), catalog)       # y compris noms avec « ; » et « # »

    def test_nommage_des_emplacements(self):
        policy = self.ports.locations
        first = policy.suggest_location("Épargne BNI", [])
        second = policy.suggest_location("Épargne BNI", [first])
        self.assertNotEqual(first, second)
        self.assertEqual(policy.canonical(first), policy.canonical(first))


class ExcelStorageTest(StorageContract, unittest.TestCase):
    make_ports = staticmethod(excel_ports)

    def path(self, name):
        return os.path.join(self.folder, name)

    def read_bytes(self, name):
        with open(self.path(name), "rb") as f:
            return f.read()

    def test_fichier_ancien_format_lisible(self):
        """Dates en texte JJ/MM/AAAA, pas de feuille « Catégories » : fichiers de la version précédente."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(["date", "categorie", "type", "libelle", "montant"])
        ws.append(["01/09/2026", "riz", "dépense", "riz", 3200])
        ws.append(["02/09/2026", "riz", "dépôt", "dépôt", 30000.0])
        wb.save(self.path("old.xlsx"))
        ledger = self.ports.ledgers.load("old.xlsx")
        self.assertEqual([t.amount for t in ledger.transactions], [3200, 30000])
        self.assertEqual(ledger.categories, ["riz"])
        self.assertEqual(len(ExcelTransactionImporter().read(self.path("old.xlsx"))), 2)

    def test_fichier_invalide_leve_storage_error(self):
        wb = Workbook()
        wb.active.title = "Transactions"
        wb.active.append(["date", "categorie", "type", "libelle", "montant"])
        wb.active.append(["01/09/2026", "riz", "virement", "x", 100])
        wb.save(self.path("bad.xlsx"))
        with self.assertRaises(StorageError) as caught:
            self.ports.ledgers.load("bad.xlsx")
        self.assertIn("ligne 2", str(caught.exception))
        with open(self.path("not_excel.xlsx"), "w") as f:
            f.write("pas un classeur")
        with self.assertRaises(StorageError):
            self.ports.ledgers.load("not_excel.xlsx")

    def test_fichier_verrouille_ne_corrompt_rien(self):
        self.ports.ledgers.save("w.xlsx", sample_ledger())
        before = self.read_bytes("w.xlsx")
        with patch("os.replace", side_effect=PermissionError):
            with self.assertRaises(StorageError) as caught:
                self.ports.ledgers.save("w.xlsx", Ledger())
        self.assertTrue(caught.exception.locked)
        self.assertEqual(self.read_bytes("w.xlsx"), before)
        self.assertFalse(os.path.exists(self.path("w.xlsx.tmp")))

    def test_emplacement_hors_dossier_garde_le_chemin_complet(self):
        policy = self.ports.locations
        self.assertEqual(policy.location_from_path(self.path("x.xlsx")), "x.xlsx")
        elsewhere = os.path.abspath(os.path.join(self.folder, "..", "autre.xlsx"))
        self.assertEqual(policy.location_from_path(elsewhere), elsewhere)
        self.assertEqual(policy.storage_path("x.xlsx"), self.path("x.xlsx"))


class SqliteStorageTest(StorageContract, unittest.TestCase):
    make_ports = staticmethod(sqlite_ports)

    def test_pas_de_fichier_a_associer_ni_a_ouvrir(self):
        with self.assertRaises(DomainError):
            self.ports.locations.location_from_path("x.db")
        self.assertIsNone(self.ports.locations.storage_path("w1"))


if __name__ == "__main__":
    unittest.main()
