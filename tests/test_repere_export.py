"""Tests de la conversion Excel -> JSON « repere » (fonction pure + lecture du classeur)."""
import datetime as dt
import json
import os
import tempfile
import unittest

from openpyxl import Workbook

from suivi.adapters.driven.excel.repere_export import xlsx_to_repere, xlsx_to_repere_json
from suivi.adapters.driven.wiring import excel_ports
from suivi.application.errors import StorageError
from suivi.application.repere_format import ledgers_to_repere, stable_id
from suivi.domain.model.errors import DomainError
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.transaction import Kind

D = dt.date
NOW = dt.datetime(2026, 11, 20, 10, 30, 5, 123456, tzinfo=dt.timezone.utc)


def sample_ledger() -> Ledger:
    ledger = Ledger(initial_balance=16600, categories=["bazar", "gouter", "inutilisée"])
    ledger.add_transaction(D(2026, 9, 2), "bazar", Kind.DEPOSIT, "", 52700)
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.EXPENSE, "œuf et pâtes", 900)
    ledger.add_transaction(D(2026, 9, 1), "gouter", Kind.EXPENSE, "wifi", 500)
    ledger.set_daily_budget("bazar", 3700)
    return ledger


def only_wallet(export):
    return export["wallets"][0]


class RepereFormatTest(unittest.TestCase):
    def test_structure_et_valeurs(self):
        export = ledgers_to_repere([("Principal", sample_ledger())], exported_at=NOW)
        self.assertEqual((export["format"], export["version"]), ("repere", 1))
        self.assertEqual(export["exportedAt"], "2026-11-20T10:30:05.123Z")
        wallet = only_wallet(export)
        self.assertEqual(export["activeWalletId"], wallet["id"])
        self.assertEqual((wallet["name"], wallet["initialBalance"]), ("Principal", 16600))
        self.assertEqual([c["name"] for c in wallet["categories"]], ["bazar", "gouter", "inutilisée"])
        self.assertEqual(wallet["categories"][0], {"name": "bazar", "dailyBudget": 3700, "initialBalance": 0})
        self.assertEqual([t["date"] for t in wallet["transactions"]], ["2026-09-01", "2026-09-01", "2026-09-02"])
        self.assertEqual({t["kind"] for t in wallet["transactions"]}, {"deposit", "expense"})
        self.assertEqual(wallet["transactions"][-1]["amount"], 52700)

    def test_identifiants_stables_et_uniques(self):
        ledger = Ledger(categories=["a"])
        for _ in range(2):   # deux lignes strictement identiques
            ledger.add_transaction(D(2026, 9, 1), "a", Kind.EXPENSE, "pain", 100)
        first = ledgers_to_repere([("W", ledger)], exported_at=NOW)
        second = ledgers_to_repere([("W", ledger)], exported_at=NOW)
        ids = [t["id"] for t in only_wallet(first)["transactions"]]
        self.assertEqual(ids, [t["id"] for t in only_wallet(second)["transactions"]])
        self.assertEqual(len(set(ids)), 2)
        self.assertRegex(ids[0], r"^id-[0-9a-z]{8}-[0-9a-z]{8}$")
        self.assertEqual(stable_id("x", 1), stable_id("x", 1))
        self.assertNotEqual(stable_id("x", 1), stable_id("x", 2))

    def test_date_de_debut_reporte_les_soldes(self):
        export = ledgers_to_repere([("W", sample_ledger())], start=D(2026, 9, 2), exported_at=NOW)
        wallet = only_wallet(export)
        self.assertEqual(len(wallet["transactions"]), 1)
        starts = {c["name"]: c["initialBalance"] for c in wallet["categories"]}
        self.assertEqual(starts, {"bazar": -900, "gouter": -500, "inutilisée": 0})
        self.assertEqual(wallet["initialBalance"], 16600)   # le solde du portefeuille ne bouge pas

    def test_portefeuille_actif_et_erreurs(self):
        export = ledgers_to_repere([("A", Ledger()), ("B", Ledger())], active="B", exported_at=NOW)
        self.assertEqual(export["activeWalletId"], export["wallets"][1]["id"])
        for call in (lambda: ledgers_to_repere([]),
                     lambda: ledgers_to_repere([("A", Ledger()), ("A", Ledger())]),
                     lambda: ledgers_to_repere([("A", Ledger())], active="Z")):
            with self.assertRaises(DomainError):
                call()

    def test_heure_naive_et_serialisable(self):
        export = ledgers_to_repere([("W", sample_ledger())])   # exportedAt par défaut
        self.assertTrue(export["exportedAt"].endswith("Z"))
        json.dumps(export)


class XlsxToRepereTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def test_depuis_un_classeur_de_l_application(self):
        excel_ports(self.folder).ledgers.save("caisse.xlsx", sample_ledger())
        export = xlsx_to_repere(os.path.join(self.folder, "caisse.xlsx"), exported_at=NOW)
        wallet = only_wallet(export)
        self.assertEqual(wallet["name"], "caisse")
        self.assertEqual((len(wallet["transactions"]), wallet["initialBalance"]), (3, 16600))

    def test_depuis_un_classeur_saisi_a_la_main(self):
        book = Workbook()
        sheet = book.active
        sheet.title = "Transactions"
        sheet.append(["date", "categorie", "type", "libelle", "montant"])
        sheet.append(["01/09/2026", "bazar", "dépense", "pain", 900])
        sheet.append(["02/09/2026", "bazar", "depot", None, 5000])
        categories = book.create_sheet("Catégories")
        categories.append(["categorie", "budget_jour"])
        categories.append(["bazar", 3700])
        settings = book.create_sheet("Paramètres")
        settings.append(["parametre", "valeur"])
        settings.append(["solde_initial", 1000])
        path = os.path.join(self.folder, "main.xlsx")
        book.save(path)

        wallet = only_wallet(xlsx_to_repere(path, wallet_name="Mvola", exported_at=NOW))
        self.assertEqual((wallet["name"], wallet["initialBalance"]), ("Mvola", 1000))
        self.assertEqual([t["kind"] for t in wallet["transactions"]], ["expense", "deposit"])
        self.assertEqual(wallet["categories"], [{"name": "bazar", "dailyBudget": 3700, "initialBalance": 0}])

    def test_texte_json(self):
        excel_ports(self.folder).ledgers.save("c.xlsx", sample_ledger())
        text = xlsx_to_repere_json(os.path.join(self.folder, "c.xlsx"), exported_at=NOW)
        self.assertIn("œuf et pâtes", text)   # accents conservés
        self.assertEqual(json.loads(text)["format"], "repere")

    def test_fichier_introuvable_ou_invalide(self):
        with self.assertRaises(StorageError):
            xlsx_to_repere(os.path.join(self.folder, "absent.xlsx"))
        broken = os.path.join(self.folder, "casse.xlsx")
        with open(broken, "w", encoding="utf-8") as f:
            f.write("pas un classeur")
        with self.assertRaises(StorageError):
            xlsx_to_repere(broken)


if __name__ == "__main__":
    unittest.main()
