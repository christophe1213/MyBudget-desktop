"""Tableau de bord : calculs du domaine, contrôleur (filtre entre deux dates) et dessinateurs."""
import datetime as dt
import unittest
from collections import Counter

from suivi.adapters.driving.gui.contract.dto import FlowChartData, PieData, PieSlice, TransactionForm
from suivi.adapters.driving.gui.dashboard_painter import DashboardPalette, FlowPainter, PiePainter
from suivi.bootstrap import build_application
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.period import Period
from suivi.domain.model.transaction import Kind
from suivi.domain.services.dashboard import DashboardAnalyzer

from .fakes import make_ports, make_ui
from .test_chart_painter import FakeCanvas

D = dt.date


def sample() -> Ledger:
    ledger = Ledger(categories=["Alimentation", "Transport", "Électricité", "Imprévus", "Loisirs"])
    for category, amount in [("Alimentation", 30000), ("Transport", 20000), ("Électricité", 20000),
                             ("Loisirs", 10000), ("Imprévus", 10000)]:
        ledger.add_transaction(D(2026, 10, 14), category, Kind.DEPOSIT, "", amount)
    ledger.add_transaction(D(2026, 10, 15), "Alimentation", Kind.EXPENSE, "marché", 12000)
    ledger.add_transaction(D(2026, 10, 20), "Électricité", Kind.EXPENSE, "Jirama", 4000)
    ledger.add_transaction(D(2026, 10, 20), "Imprévus", Kind.EXPENSE, "panne", 14000)   # dépasse les dépôts : déficit
    return ledger


class DashboardDomainTest(unittest.TestCase):
    def test_soldes_restants_par_budget(self):
        shares = DashboardAnalyzer().budget_shares(sample())
        self.assertEqual([(i.category, i.balance) for i in shares.items],
                         [("Transport", 20000), ("Alimentation", 18000), ("Électricité", 16000), ("Loisirs", 10000)])
        self.assertEqual(shares.total, 64000)
        self.assertEqual(shares.deficits, (("Imprévus", 4000),))        # solde négatif : hors camembert
        self.assertEqual(shares.deficit_total, 4000)
        self.assertAlmostEqual(sum(i.share for i in shares.items), 100, delta=0.2)

    def test_un_solde_nul_n_apparait_pas(self):
        ledger = Ledger(categories=["a"])
        ledger.add_transaction(D(2026, 1, 1), "a", Kind.DEPOSIT, "", 100)
        ledger.add_transaction(D(2026, 1, 2), "a", Kind.EXPENSE, "", 100)
        self.assertEqual(DashboardAnalyzer().budget_shares(ledger).items, ())

    def test_flux_un_point_par_jour_zeros_compris(self):
        series = DashboardAnalyzer().flows(sample(), Period(D(2026, 10, 14), D(2026, 10, 20)))
        self.assertEqual(len(series.days), 7)
        self.assertEqual([d.expenses for d in series.days], [0, 12000, 0, 0, 0, 0, 18000])
        self.assertEqual((series.total_deposits, series.total_expenses), (90000, 30000))

    def test_pic_des_sorties_avec_son_detail_par_categorie(self):
        series = DashboardAnalyzer().flows(sample(), Period(D(2026, 10, 14), D(2026, 10, 20)))
        self.assertEqual(series.peak_expense_day.date, D(2026, 10, 20))
        self.assertEqual(series.peak_expense_breakdown, (("Imprévus", 14000), ("Électricité", 4000)))
        self.assertEqual(series.peak_deposit_day.date, D(2026, 10, 14))

    def test_le_filtre_restreint_les_totaux(self):
        series = DashboardAnalyzer().flows(sample(), Period(D(2026, 10, 16), D(2026, 10, 19)))
        self.assertEqual((series.total_deposits, series.total_expenses, series.peak_expense_day), (0, 0, None))


class DashboardControllerTest(unittest.TestCase):
    def setUp(self):
        self.ports, self.ui = make_ports(), make_ui()
        self.ports.ledgers.stored["principal"] = sample()
        self.app = build_application(self.ui, self.ports, "/export")
        self.app.start()
        self.listener = self.ui.dashboard.set_listener.call_args[0][0]

    def flows(self):
        return self.ui.dashboard.show_flows.call_args[0][0]

    def test_affichage_initial_camembert_et_periode_par_defaut(self):
        pie = self.ui.dashboard.show_budget_shares.call_args[0][0]
        self.assertEqual([s.label for s in pie.slices], ["Transport", "Alimentation", "Électricité", "Loisirs"])
        self.assertEqual(pie.slices[0].amount_text, "20 000 Ar")
        self.assertEqual(pie.slices[0].percent_text, "31,2 %")           # 20 000 / 64 000 ; virgule décimale française
        self.assertIn("4 000 Ar en déficit (Imprévus)", pie.note)         # le déficit est expliqué sous le camembert
        self.ui.dashboard.set_period.assert_called_with("14/10/2026", "20/10/2026")
        self.assertEqual(self.flows().labels[0], "14 oct.")
        self.assertEqual(self.flows().labels[-1], "20 oct.")

    def test_courbes_et_note(self):
        data = self.flows()
        self.assertEqual(data.deposits, [90000, 0, 0, 0, 0, 0, 0])
        self.assertEqual(data.expenses, [0, 12000, 0, 0, 0, 0, 18000])
        self.assertEqual((data.deposits_text, data.expenses_text), ("Entrées · 90 000 Ar", "Sorties · 30 000 Ar"))
        self.assertIn("Le 20 octobre : Imprévus 14 000 Ar + Électricité 4 000 Ar.", data.note)

    def test_filtre_entre_deux_dates(self):
        self.ui.dashboard.get_period.return_value = ("15/10/2026", "17/10/2026")
        self.listener.on_apply_filter()
        data = self.flows()
        self.assertEqual((data.labels, data.expenses), (["15 oct.", "16 oct.", "17 oct."], [12000, 0, 0]))
        self.assertEqual(data.deposits_text, "Entrées · 0 Ar")
        self.assertIn("Entrées : 0 Ar à chaque date.", data.note)

    def test_filtre_invalide_previent_sans_effacer_le_graphique(self):
        self.ui.dashboard.show_flows.reset_mock()
        for bad in (("pas une date", "17/10/2026"), ("20/10/2026", "14/10/2026")):   # format faux ; dates inversées
            self.ui.dashboard.get_period.return_value = bad
            self.listener.on_apply_filter()
        self.assertEqual(self.ui.dialogs.warning.call_count, 2)
        self.ui.dashboard.show_flows.assert_not_called()

    def test_raccourcis_de_periode(self):
        self.listener.on_preset(3)
        self.ui.dashboard.set_period.assert_called_with("18/10/2026", "20/10/2026")
        self.assertEqual(len(self.flows().labels), 3)
        self.listener.on_preset(None)
        self.ui.dashboard.set_period.assert_called_with("14/10/2026", "20/10/2026")

    def test_une_nouvelle_transaction_met_a_jour_les_graphiques_en_gardant_le_filtre(self):
        self.ui.dashboard.get_period.return_value = ("14/10/2026", "16/10/2026")
        self.listener.on_apply_filter()
        self.ui.transactions.get_form.return_value = TransactionForm("16/10/2026", "Transport", "dépense", "taxi", "5000")
        self.ui.transactions.set_listener.call_args[0][0].on_add()
        self.assertEqual(self.flows().expenses, [0, 12000, 5000])         # la période choisie est conservée
        pie = self.ui.dashboard.show_budget_shares.call_args[0][0]
        self.assertEqual([(s.label, s.amount_text) for s in pie.slices[:3]],     # Transport tombe à 15 000 : l'ordre est recalculé
                         [("Alimentation", "18 000 Ar"), ("Électricité", "16 000 Ar"), ("Transport", "15 000 Ar")])

    def test_sans_solde_positif_pas_de_camembert(self):
        ports, ui = make_ports(), make_ui()
        build_application(ui, ports, "/export").start()
        self.assertIsNone(ui.dashboard.show_budget_shares.call_args[0][0])


class DashboardPaintersTest(unittest.TestCase):
    def pie(self, count):
        return PieData(tuple(PieSlice(f"B{i}", 10 + i, f"{10 + i} Ar", "10,0 %") for i in range(count)), "note")

    @staticmethod
    def kinds(canvas):
        return Counter(name for name, _a, _k in canvas.calls)

    def test_camembert_une_part_par_budget_et_une_ligne_de_legende_chacune(self):
        canvas = FakeCanvas(700, 320)
        PiePainter().draw(canvas, self.pie(4))
        self.assertEqual(self.kinds(canvas)["create_arc"], 4)
        self.assertEqual(self.kinds(canvas)["create_text"], 8)            # nom + « montant · pourcentage »
        arcs = [k for name, _a, k in canvas.calls if name == "create_arc"]
        self.assertAlmostEqual(sum(k["extent"] for k in arcs), -360, places=5)   # le disque est complet
        self.assertEqual(arcs[0]["start"], 90.0)                                 # départ en haut

    def test_un_seul_budget_donne_un_disque_plein(self):
        canvas = FakeCanvas(700, 320)
        PiePainter().draw(canvas, self.pie(1))
        self.assertEqual((self.kinds(canvas)["create_oval"], self.kinds(canvas)["create_arc"]), (1, 0))

    def test_courbes_deux_series_valeurs_et_dates(self):
        data = FlowChartData([f"{d} oct." for d in range(14, 21)], [0] * 7, [24, 12, 0, 5, 0, 5, 14], "Entrées · 0 Ar",
                             "Sorties · 60 Ar", "note")
        canvas, palette = FakeCanvas(760, 300), DashboardPalette()
        FlowPainter(palette).draw(canvas, data)
        polylines = [k["fill"] for name, _a, k in canvas.calls if name == "create_line" and len(_a) >= 6]
        self.assertEqual(polylines, [palette.deposits, palette.expenses])
        texts = [k["text"] for name, _a, k in canvas.calls if name == "create_text"]
        self.assertIn("14 oct.", texts)
        self.assertIn("Sorties · 60 Ar", texts)

    def test_longue_periode_n_ecrit_pas_toutes_les_valeurs(self):
        n = 90
        data = FlowChartData([f"j{i}" for i in range(n)], [i % 7 for i in range(n)], [i % 5 for i in range(n)],
                             "Entrées", "Sorties", "note")
        canvas = FakeCanvas(900, 320)
        FlowPainter().draw(canvas, data)
        texts = [k["text"] for name, _a, k in canvas.calls if name == "create_text"]
        self.assertLess(len(texts), 40)                                   # dates espacées, pas de valeurs sur les points

    def test_un_seul_jour_et_cas_vides_ne_plantent_pas(self):
        canvas = FakeCanvas(760, 300)
        FlowPainter().draw(canvas, FlowChartData(["1 oct."], [0], [5], "E", "S", ""))
        FlowPainter().draw(canvas, None)
        PiePainter().draw(canvas, None)
        small = FakeCanvas(100, 80)
        FlowPainter().draw(small, FlowChartData(["1 oct."], [0], [5], "E", "S", ""))
        PiePainter().draw(small, self.pie(3))
        self.assertEqual(small.calls, [])


if __name__ == "__main__":
    unittest.main()
