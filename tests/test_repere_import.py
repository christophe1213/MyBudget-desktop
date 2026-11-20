"""Tests de la réception : JSON « repere » -> livres de comptes -> classeurs Excel."""
import copy
import datetime as dt
import json
import os
import tempfile
import unittest

from suivi.adapters.driven.excel.repere_export import xlsx_to_repere
from suivi.adapters.driven.excel.repere_to_xlsx import repere_file_to_xlsx, repere_to_xlsx
from suivi.adapters.driven.wiring import excel_ports
from suivi.application.errors import StorageError
from suivi.application.repere_format import ledgers_to_repere
from suivi.application.repere_import import new_transactions, repere_to_ledgers
from suivi.domain.model.errors import DomainError
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.transaction import Kind

D = dt.date


def sample_ledger() -> Ledger:
    ledger = Ledger(initial_balance=16600, categories=["bazar", "gouter", "inutilisée"])
    ledger.add_transaction(D(2026, 9, 2), "bazar", Kind.DEPOSIT, "", 52700)
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.EXPENSE, "œuf et pâtes", 900)
    ledger.add_transaction(D(2026, 9, 1), "gouter", Kind.EXPENSE, "wifi", 500)
    ledger.set_daily_budget("bazar", 3700)
    return ledger


def snapshot(ledger: Ledger):
    return (sorted(ledger.transactions, key=lambda t: (t.date, t.category, t.label, t.amount)),
            ledger.initial_balance, ledger.categories, ledger.budgets)


def payload() -> dict:
    return ledgers_to_repere([("Principal", sample_ledger()), ("Mvola", Ledger(categories=["x"]))])


class ReceptionTest(unittest.TestCase):
    def test_aller_retour_exact(self):
        reception = repere_to_ledgers(payload())
        self.assertEqual([w.name for w in reception.wallets], ["Principal", "Mvola"])
        self.assertEqual(snapshot(reception.wallets[0].ledger), snapshot(sample_ledger()))
        self.assertEqual(reception.active, "Principal")
        self.assertEqual(reception.warnings, ())

    def test_accepte_texte_et_octets(self):
        text = json.dumps(payload(), ensure_ascii=False)
        for data in (text, text.encode("utf-8")):
            self.assertEqual(len(repere_to_ledgers(data).wallets), 2)

    def test_portefeuille_actif(self):
        data = payload()
        data["activeWalletId"] = data["wallets"][1]["id"]
        self.assertEqual(repere_to_ledgers(data).active, "Mvola")
        data["activeWalletId"] = "inconnu"
        self.assertEqual(repere_to_ledgers(data).active, "Principal")

    def test_entier_ecrit_en_decimal_accepte(self):
        data = payload()
        data["wallets"][0]["transactions"][0]["amount"] = 900.0
        self.assertEqual(repere_to_ledgers(data).wallets[0].ledger.transactions[0].amount, 900)

    def test_solde_de_depart_de_categorie_signale(self):
        data = payload()
        data["wallets"][0]["categories"][0]["initialBalance"] = -900
        reception = repere_to_ledgers(data)
        self.assertEqual(len(reception.warnings), 1)
        self.assertIn("bazar", reception.warnings[0])

    def test_donnees_invalides_refusees(self):
        def change(edit):
            data = copy.deepcopy(payload())
            edit(data)
            return data

        bad = {
            "format": change(lambda d: d.update(format="autre")),
            "version": change(lambda d: d.update(version=2)),
            "sans portefeuille": change(lambda d: d.update(wallets=[])),
            "nom vide": change(lambda d: d["wallets"][0].update(name="  ")),
            "noms en double": change(lambda d: d["wallets"][1].update(name="principal")),
            "type inconnu": change(lambda d: d["wallets"][0]["transactions"][0].update(kind="virement")),
            "montant nul": change(lambda d: d["wallets"][0]["transactions"][0].update(amount=0)),
            "montant décimal": change(lambda d: d["wallets"][0]["transactions"][0].update(amount=12.5)),
            "montant booléen": change(lambda d: d["wallets"][0]["transactions"][0].update(amount=True)),
            "montant texte": change(lambda d: d["wallets"][0]["transactions"][0].update(amount="900")),
            "date mal formée": change(lambda d: d["wallets"][0]["transactions"][0].update(date="01/09/2026")),
            "date inexistante": change(lambda d: d["wallets"][0]["transactions"][0].update(date="2026-02-30")),
            "catégorie vide": change(lambda d: d["wallets"][0]["transactions"][0].update(category="")),
            "budget négatif": change(lambda d: d["wallets"][0]["categories"][0].update(dailyBudget=-1)),
            "transactions pas une liste": change(lambda d: d["wallets"][0].update(transactions="x")),
        }
        for label, data in bad.items():
            with self.subTest(label), self.assertRaises(DomainError):
                repere_to_ledgers(data)
        for data in ("pas du json", b"\xff\xfe", "[1, 2]", None):
            with self.subTest(repr(data)), self.assertRaises(DomainError):
                repere_to_ledgers(data)


class MergeTest(unittest.TestCase):
    def test_recevoir_deux_fois_ne_cree_rien(self):
        self.assertEqual(new_transactions(sample_ledger(), sample_ledger()), [])

    def test_seules_les_nouvelles_transactions_restent(self):
        incoming = sample_ledger()
        incoming.add_transaction(D(2026, 9, 3), "gouter", Kind.EXPENSE, "thé", 300)
        fresh = new_transactions(sample_ledger(), incoming)
        self.assertEqual([(t.label, t.amount) for t in fresh], [("thé", 300)])

    def test_les_doublons_exacts_sont_comptes(self):
        local, incoming = Ledger(categories=["a"]), Ledger(categories=["a"])
        local.add_transaction(D(2026, 9, 1), "a", Kind.EXPENSE, "pain", 100)
        for _ in range(2):
            incoming.add_transaction(D(2026, 9, 1), "a", Kind.EXPENSE, "pain", 100)
        self.assertEqual(len(new_transactions(local, incoming)), 1)

    def test_fusion_dans_le_domaine(self):
        local = sample_ledger()
        incoming = sample_ledger()
        incoming.add_category("nouvelle")
        incoming.add_transaction(D(2026, 9, 3), "nouvelle", Kind.DEPOSIT, "", 10)
        local.merge(new_transactions(local, incoming))
        self.assertEqual((len(local.transactions), "nouvelle" in local.categories), (4, True))


class XlsxWriteTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def load(self, path):
        return excel_ports(self.folder).ledgers.load(path)

    def test_un_classeur_par_portefeuille_relisible(self):
        result = repere_to_xlsx(payload(), self.folder)
        self.assertEqual([n for n, _ in result.files], ["Principal", "Mvola"])
        self.assertEqual([os.path.basename(p) for _, p in result.files],
                         ["transactions_principal.xlsx", "transactions_mvola.xlsx"])
        self.assertEqual(snapshot(self.load(result.files[0][1])), snapshot(sample_ledger()))

    def test_ne_jamais_ecraser(self):
        first = repere_to_xlsx(payload(), self.folder, wallet="Principal")
        second = repere_to_xlsx(payload(), self.folder, wallet="Principal")
        self.assertEqual(os.path.basename(second.files[0][1]), "transactions_principal_2.xlsx")
        self.assertNotEqual(first.files[0][1], second.files[0][1])

    def test_choix_par_nom_ou_identifiant_et_inconnu(self):
        data = payload()
        by_id = repere_to_xlsx(data, self.folder, wallet=data["wallets"][1]["id"])
        self.assertEqual([n for n, _ in by_id.files], ["Mvola"])
        with self.assertRaises(DomainError):
            repere_to_xlsx(data, self.folder, wallet="Absent")

    def test_dossier_cree_et_donnees_invalides_n_ecrivent_rien(self):
        target = os.path.join(self.folder, "sous", "dossier")
        bad = payload()
        bad["wallets"][1]["transactions"] = [{"date": "x"}]   # 2e portefeuille invalide : rien n'est écrit
        with self.assertRaises(DomainError):
            repere_to_xlsx(bad, target)
        self.assertFalse(os.path.exists(target))
        repere_to_xlsx(payload(), target)
        self.assertTrue(os.path.isdir(target))

    def test_avertissements_des_seuls_portefeuilles_ecrits(self):
        data = payload()
        data["wallets"][1]["categories"][0]["initialBalance"] = 50
        self.assertEqual(repere_to_xlsx(data, self.folder, wallet="Principal").warnings, ())
        self.assertEqual(len(repere_to_xlsx(data, self.folder, wallet="Mvola").warnings), 1)

    def test_depuis_un_fichier_json(self):
        path = os.path.join(self.folder, "recu.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload(), f, ensure_ascii=False)
        out = os.path.join(self.folder, "sortie")
        self.assertEqual(len(repere_file_to_xlsx(path, out).files), 2)
        self.assertEqual(len(repere_file_to_xlsx(path).files), 2)   # défaut : dossier du fichier JSON
        with self.assertRaises(StorageError):
            repere_file_to_xlsx(os.path.join(self.folder, "absent.json"))

    def test_cycle_complet_xlsx_json_xlsx(self):
        excel_ports(self.folder).ledgers.save("depart.xlsx", sample_ledger())
        exported = xlsx_to_repere(os.path.join(self.folder, "depart.xlsx"))
        result = repere_to_xlsx(exported, os.path.join(self.folder, "arrivee"))
        self.assertEqual(snapshot(self.load(result.files[0][1])), snapshot(sample_ledger()))


if __name__ == "__main__":
    unittest.main()
