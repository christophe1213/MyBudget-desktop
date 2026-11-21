"""Synchronisation de bout en bout : appareil (WebSocket réel) <-> serveur <-> vue ctk <-> contrôleur <-> cas
d'usage <-> classeurs Excel. Seule la bibliothèque graphique est simulée (comme dans test_tk_views_smoke)."""
import datetime as dt
import importlib
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from suivi.adapters.driven.sync_journal import TextSyncJournal
from suivi.adapters.driven.wiring import excel_ports
from suivi.adapters.driving.gui.contract.interfaces import Dialogs
from suivi.application.errors import StorageError
from suivi.application.ports.outbound import SyncJournal
from suivi.application.repere_format import ledgers_to_repere
from suivi.application.use_cases.sync import SyncUseCase
from suivi.bootstrap import build_application
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.transaction import Kind
from tests.ws_client import WsClient, free_port

D = dt.date


class FakeStringVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, _mode, _callback):
        pass


def fake_gui_modules():
    tk, ctk = MagicMock(), MagicMock()
    tk.StringVar = ctk.StringVar = ctk.BooleanVar = FakeStringVar
    canvas = MagicMock()                       # les graphiques se dessinent sur ce canevas simulé
    canvas.winfo_width.return_value, canvas.winfo_height.return_value = 900, 300
    canvas.bbox.return_value = (0, 0, 60, 10)
    tk.Canvas = MagicMock(return_value=canvas)
    return {"tkinter": tk, "tkinter.ttk": MagicMock(), "tkinter.messagebox": MagicMock(),
            "tkinter.filedialog": MagicMock(), "tkinter.simpledialog": MagicMock(), "customtkinter": ctk}


def forget_gui_modules():
    for name in [m for m in sys.modules if m.startswith(("suivi.adapters.driving.gui.tk",
                                                         "suivi.adapters.driving.gui.ctk"))]:
        del sys.modules[name]


def principal() -> Ledger:
    ledger = Ledger(categories=["bazar", "gouter"])
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.DEPOSIT, "", 10000)
    ledger.add_transaction(D(2026, 9, 1), "bazar", Kind.EXPENSE, "tomates", 3000)
    ledger.add_transaction(D(2026, 9, 3), "gouter", Kind.EXPENSE, "thé", 500)
    return ledger


class SyncFlowTest(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(sys.modules, fake_gui_modules())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(forget_gui_modules)
        forget_gui_modules()
        self.folder = tempfile.mkdtemp()
        self.ports = excel_ports(self.folder)
        self.ports.ledgers.save("transactions.xlsx", principal())
        module = importlib.import_module("suivi.adapters.driving.gui.ctk.user_interface")
        self.ui = module.CtkUserInterface("Test")
        self.dialogs = MagicMock(spec=Dialogs)
        self.ui.dialogs = self.dialogs
        self.journal_path = os.path.join(self.folder, "journal.txt")
        self.app = build_application(self.ui, self.ports, self.folder, "Test", None, TextSyncJournal(self.journal_path))
        self.app.start()
        self.app.wallets.create("Caisse")               # second portefeuille (non actif ensuite)
        self.app.wallets.open("Principal")
        self.view = self.ui.sync
        self.confirm = MagicMock(return_value=True)      # l'utilisateur confirme ; la vraie fenêtre est testée à part
        self.view.confirm_transfer = self.confirm
        self.view._server_port.set(str(free_port()))
        self.view.start()
        self.addCleanup(self.view.stop)
        self.assertIn("Serveur actif", self.view._status.get())
        self.client = WsClient(self.view._server.port, self.view._server.token)
        self.addCleanup(self.client.close)
        self.pump_until(lambda: self.view.device_count() == 1)

    # ---- outils -------------------------------------------------------------------------------------------
    def pump_until(self, condition, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            self.view._pump()            # ce que fait la boucle graphique toutes les 150 ms
            if condition():
                return True
            time.sleep(0.02)
        self.fail("condition jamais atteinte")

    def journal(self) -> str:
        with open(self.journal_path, encoding="utf-8") as f:
            return f.read()

    def stored(self, location="transactions.xlsx") -> Ledger:
        return self.ports.ledgers.load(location)

    def caisse_location(self) -> str:
        return next(s.location for s in self.app.wallets.summaries() if s.name == "Caisse")

    def client_sends(self, payload) -> dict:
        return self.reply_after(lambda: self.client.send_text(json.dumps({"type": "data", "payload": payload})))

    def incoming(self, principal_extra=(), caisse_extra=(), extra_wallet=None):
        a = principal()
        for day, category, label, amount in principal_extra:
            a.add_transaction(day, category, Kind.EXPENSE, label, amount)
        b = Ledger(categories=["transport"])
        for day, label, amount in caisse_extra:
            b.add_transaction(day, "transport", Kind.EXPENSE, label, amount)
        wallets = [("Principal", a), ("Caisse", b)]
        if extra_wallet:
            wallets.append((extra_wallet, Ledger()))
        return ledgers_to_repere(wallets)

    def reply_after(self, action):
        action()
        self.pump_until(lambda: self.client.has_data())   # la vue traite le message, puis la réponse arrive
        return json.loads(self.client.recv_text())

    # ---- envoi -------------------------------------------------------------------------------------------
    def test_envoyer_a_partir_d_une_date(self):
        self.view._start_date.set("02/09/2026")
        self.view._listener.on_send()
        message = json.loads(self.client.recv_text())
        self.assertEqual(message["type"], "data")
        wallets = {w["name"]: w for w in message["payload"]["wallets"]}
        self.assertEqual(set(wallets), {"Principal", "Caisse"})
        self.assertEqual([t["date"] for t in wallets["Principal"]["transactions"]], ["2026-09-03"])
        carried = {c["name"]: c["initialBalance"] for c in wallets["Principal"]["categories"]}
        self.assertEqual(carried, {"bazar": 7000, "gouter": 0})        # 10 000 - 3 000 reportés
        self.assertEqual(message["payload"]["activeWalletId"], wallets["Principal"]["id"])
        self.assertIn("ENVOI", self.journal())
        self.assertIn("depuis le 02/09/2026", self.journal())
        # la liste affichée avant l'envoi est exactement ce qui part, puis une boîte de message conclut
        title, heading, notes, rows, confirm_label = self.confirm.call_args.args
        self.assertEqual((title, confirm_label), ("Confirmer l'envoi", "Envoyer"))
        self.assertIn("1 transaction(s)", heading)
        self.assertIn("depuis le 02/09/2026", heading)
        self.assertEqual([r.values for r in rows], [("Principal", "03/09/2026", "gouter", "thé", "-500 Ar")])
        self.assertTrue(any("bazar 7 000 Ar" in n for n in notes))
        self.dialogs.info.assert_called_once()
        self.assertEqual(self.dialogs.info.call_args.args[0], "Envoi terminé")

    def test_envoi_annule_ne_part_pas(self):
        self.confirm.return_value = False
        self.view._listener.on_send()
        self.confirm.assert_called_once()
        self.assertFalse(self.client.has_data(0.3))                  # rien n'est parti
        self.assertIn("Envoi annulé", self.journal())
        self.dialogs.info.assert_not_called()

    def test_envoyer_tout_l_historique(self):
        self.view._listener.on_send()
        payload = json.loads(self.client.recv_text())["payload"]
        principal_wallet = next(w for w in payload["wallets"] if w["name"] == "Principal")
        self.assertEqual(len(principal_wallet["transactions"]), 3)
        self.assertIn("tout l'historique", self.journal())

    def test_envoyer_refuse_une_date_invalide_et_sans_appareil(self):
        self.view._start_date.set("pas une date")
        self.view._listener.on_send()
        self.dialogs.warning.assert_called()
        self.assertNotIn("ENVOI", self.journal())
        self.client.close()
        self.pump_until(lambda: self.view.device_count() == 0)
        self.view._start_date.set("")
        self.view._listener.on_send()
        self.dialogs.info.assert_called()

    # ---- récupération --------------------------------------------------------------------------------------
    def test_recuperer_demande_les_donnees_a_l_appareil(self):
        self.view._listener.on_fetch()
        self.assertEqual(json.loads(self.client.recv_text()), {"type": "request"})
        self.assertIn("DEMANDE", self.journal())
        self.assertEqual(self.dialogs.info.call_args.args[0], "Demande envoyée")

    def test_reception_fusionne_sans_doublon_dans_chaque_portefeuille(self):
        payload = self.incoming(principal_extra=[(D(2026, 9, 4), "bazar", "pain", 800)],
                                caisse_extra=[(D(2026, 9, 5), "bus", 1200)], extra_wallet="Inconnu")
        reply = self.reply_after(lambda: self.client.send_text(json.dumps({"type": "data", "payload": payload})))
        self.assertEqual(reply["type"], "ack")
        self.assertIn("Principal : 1 ajoutée(s), 3 déjà présente(s)", reply["message"])
        self.assertIn("Caisse : 1 ajoutée(s)", reply["message"])
        self.assertIn("Inconnu : portefeuille inconnu ici (ignoré)", reply["message"])
        self.assertEqual(len(self.stored().transactions), 4)                       # portefeuille actif
        caisse = self.stored(self.caisse_location())                                # non actif : écrit aussi
        self.assertEqual([t.label for t in caisse.transactions], ["bus"])
        self.assertIn("transport", caisse.categories)
        self.assertIn("RECEPTION", self.journal())
        # avant d'ajouter : la liste des nouvelles transactions, avec leur portefeuille ; après : une boîte de message
        title, heading, notes, rows, confirm_label = self.confirm.call_args.args
        self.assertEqual((title, confirm_label), ("Confirmer la réception", "Ajouter"))
        self.assertIn("2 transaction(s)", heading)
        self.assertEqual(sorted((r.values[0], r.values[3]) for r in rows), [("Caisse", "bus"), ("Principal", "pain")])
        self.assertTrue(any("Inconnu" in n and "ignoré" in n for n in notes))
        self.assertEqual(self.dialogs.info.call_args.args[0], "Réception terminée")

        again = self.reply_after(lambda: self.client.send_text(json.dumps({"type": "data", "payload": payload})))
        self.assertIn("Principal : déjà à jour", again["message"])
        self.confirm.assert_called_once()                       # rien de nouveau : pas de confirmation inutile
        self.assertEqual(self.dialogs.info.call_count, 2)       # mais le résultat est annoncé
        self.assertEqual(len(self.stored().transactions), 4)                       # idempotent
        self.assertEqual(len(self.stored(self.caisse_location()).transactions), 1)

    def test_reception_refusee_ne_modifie_rien(self):
        before = (self.stored().transactions, self.stored(self.caisse_location()).transactions)
        self.confirm.return_value = False
        reply = self.client_sends(self.incoming(principal_extra=[(D(2026, 9, 4), "bazar", "pain", 800)],
                                                caisse_extra=[(D(2026, 9, 5), "bus", 1200)]))
        self.assertEqual(reply["type"], "error")
        self.assertIn("refusée", reply["message"])
        self.assertEqual((self.stored().transactions, self.stored(self.caisse_location()).transactions), before)
        self.assertIn("réception refusée", self.journal())
        self.dialogs.info.assert_not_called()

    def test_apercu_ne_modifie_rien(self):
        sync = self.view._listener._sync
        preview = sync.preview_receive(self.incoming(principal_extra=[(D(2026, 9, 4), "bazar", "pain", 800)],
                                                     caisse_extra=[(D(2026, 9, 5), "bus", 1200)],
                                                     extra_wallet="Inconnu"))
        self.assertTrue(preview.has_changes)
        by_name = {w.name: w for w in preview.wallets}
        self.assertEqual((len(by_name["Principal"].transactions), by_name["Principal"].already_present), (1, 3))
        self.assertEqual(by_name["Caisse"].new_categories, ("transport",))
        self.assertIsNotNone(by_name["Inconnu"].status)
        self.assertEqual(len(self.stored().transactions), 3)                       # rien n'a été écrit
        self.assertEqual(self.stored(self.caisse_location()).transactions, ())

    def test_reception_categorie_avec_une_autre_casse(self):
        ledger = Ledger(categories=["BAZAR"])
        ledger.add_transaction(D(2026, 9, 6), "BAZAR", Kind.EXPENSE, "riz", 900)
        payload = ledgers_to_repere([("Principal", ledger)])
        self.reply_after(lambda: self.client.send_text(json.dumps({"type": "data", "payload": payload})))
        saved = self.stored()
        self.assertEqual(saved.categories, ["bazar", "gouter"])                    # pas de doublon « BAZAR »
        self.assertEqual(saved.transactions[-1].category, "bazar")

    def test_reception_invalide_ne_change_rien_et_renvoie_l_erreur(self):
        before = self.stored().transactions
        bad = self.incoming()
        bad["wallets"][0]["transactions"][0]["amount"] = -5
        for text in (json.dumps({"type": "data", "payload": bad}), "pas du json",
                     json.dumps({"type": "inconnu"}), json.dumps({"type": "data"})):
            with self.subTest(text=text[:30]):
                reply = self.reply_after(lambda t=text: self.client.send_text(t))
                self.assertEqual(reply["type"], "error")
        self.assertEqual(self.stored().transactions, before)
        self.assertIn("ERREUR", self.journal())
        self.dialogs.warning.assert_called()                       # la donnée invalide est signalée à l'utilisateur
        self.confirm.assert_not_called()                           # et rien n'a été proposé à la confirmation

    def test_un_appareil_peut_demander_les_donnees_du_pc(self):
        reply = self.reply_after(lambda: self.client.send_text(json.dumps({"type": "request", "start": "2026-09-03"})))
        wallet = next(w for w in reply["payload"]["wallets"] if w["name"] == "Principal")
        self.assertEqual([t["date"] for t in wallet["transactions"]], ["2026-09-03"])
        self.assertIn("127.0.0.1 demande vos données", self.confirm.call_args.args[1])
        bad = self.reply_after(lambda: self.client.send_text(json.dumps({"type": "request", "start": "demain"})))
        self.assertEqual(bad["type"], "error")

    def test_demande_d_un_appareil_refusee(self):
        self.confirm.return_value = False
        reply = self.reply_after(lambda: self.client.send_text(json.dumps({"type": "request"})))
        self.assertEqual(reply["type"], "error")
        self.assertIn("refusé", reply["message"])
        self.assertIn("envoi refusé", self.journal())

    def test_pendant_la_confirmation_les_messages_attendent(self):
        seen = []

        def during(*_args):
            if not seen:                                                 # une fois : un message arrive pendant la fenêtre
                self.client.send_text(json.dumps({"type": "request"}))
                time.sleep(0.2)
                self.view._pump()                                        # ce que ferait la boucle graphique
                seen.append(self.client.has_data(0.1))
            return True

        self.confirm.side_effect = during
        self.view._act("on_send")
        self.assertEqual(seen, [False])                                  # non traité tant que la fenêtre est ouverte
        self.assertEqual(json.loads(self.client.recv_text())["type"], "data")   # l'envoi voulu
        self.pump_until(lambda: self.client.has_data())
        self.assertEqual(json.loads(self.client.recv_text())["type"], "data")   # puis la demande en attente

    def test_vraie_fenetre_de_confirmation_sous_simulation(self):
        # sans interface réelle la fenêtre ne peut pas être confirmée : le résultat sûr est « Annuler »
        window = type(self.view).confirm_transfer
        self.assertFalse(window(self.view, "Titre", "Entête", ["note"], [], "OK"))

    # ---- journal et arrêt ------------------------------------------------------------------------------------
    def test_journal_affiche_au_demarrage_et_connexions_notees(self):
        self.assertIn("CONNEXION", self.journal())
        self.assertIn("Appareil connecté", self.journal())
        self.client.close()
        self.pump_until(lambda: "déconnecté" in self.journal())

    def test_arret_du_serveur(self):
        self.view.stop()
        self.assertEqual(self.view.device_count(), 0)
        self.assertEqual(self.view.send("x"), 0)
        self.assertIsNone(self.client.recv_frame())


class JournalAndUseCaseTest(unittest.TestCase):
    def test_journal_texte(self):
        folder = tempfile.mkdtemp()
        journal = TextSyncJournal(os.path.join(folder, "j.txt"))
        self.assertEqual(journal.tail(5), [])                    # pas encore de fichier
        for number in range(4):
            journal.append(f"ligne {number} é")
        self.assertEqual(journal.tail(2), ["ligne 2 é", "ligne 3 é"])
        self.assertEqual(journal.tail(0), [])
        bad = TextSyncJournal(os.path.join(folder, "absent", "j.txt"))
        with self.assertRaises(StorageError):
            bad.append("x")

    def test_un_journal_en_panne_ne_casse_pas_la_synchronisation(self):
        class Broken(SyncJournal):
            location = "nulle part"

            def append(self, line):
                raise StorageError("disque plein")

            def tail(self, count):
                raise StorageError("illisible")

        clock = MagicMock()
        clock.now.return_value = dt.datetime(2026, 11, 20, 9, 5, 7)
        use_case = SyncUseCase(MagicMock(), MagicMock(), MagicMock(), Broken(), clock, MagicMock())
        self.assertEqual(use_case.record("ENVOI", "ligne\nmultiple  espacée"),
                         "2026-11-20 09:05:07 | ENVOI     | ligne multiple espacée")
        self.assertEqual(use_case.recent_entries(), [])


if __name__ == "__main__":
    unittest.main()
