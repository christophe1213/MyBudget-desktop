"""Le dessin du graphique, avec un faux canevas (aucune bibliothèque graphique)."""
import unittest
from collections import Counter

from suivi.adapters.driving.gui.chart_painter import ChartPainter, ChartPalette, nice_step
from suivi.adapters.driving.gui.contract.dto import ChartData


class FakeCanvas:
    def __init__(self, width=800, height=260):
        self.width, self.height, self.calls = width, height, []

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def delete(self, *_):
        self.calls = []

    def bbox(self, _item):
        return (0, 0, 60, 10)

    def __getattr__(self, name):
        if name.startswith("create_"):
            def draw(*args, **kwargs):
                self.calls.append((name, args, kwargs))
                return len(self.calls)
            return draw
        raise AttributeError(name)


def data(retained=None, values=(3000, 0, 1000)):
    return ChartData([f"0{i + 1}/09" for i in range(len(values))], list(values), 1333.0, 1527.0, retained,
                     "moyenne 1 333 Ar", "budget retenu" if retained else None)


class ChartPainterTest(unittest.TestCase):
    def kinds(self, canvas):
        return Counter(name for name, _a, _k in canvas.calls)

    @staticmethod
    def bar_fills(canvas, palette):
        """Couleurs des barres (on écarte la bande d'écart-type et les pastilles de légende de 10 px)."""
        return [k["fill"] for name, a, k in canvas.calls
                if name == "create_rectangle" and abs(a[2] - a[0]) != 10 and k["fill"] != palette.band]

    def test_barres_uniquement_pour_les_jours_avec_depense(self):
        canvas, palette = FakeCanvas(), ChartPalette()
        ChartPainter(palette).draw(canvas, data())
        self.assertEqual(self.bar_fills(canvas, palette), [palette.bars, palette.bars])   # 3 jours, 1 sans dépense

    def test_jours_au_dessus_du_budget_changent_de_couleur(self):
        palette = ChartPalette(bars="#00ff00", over="#ff8800")
        canvas = FakeCanvas()
        ChartPainter(palette).draw(canvas, data(retained=2000))
        self.assertEqual(self.bar_fills(canvas, palette), ["#ff8800", "#00ff00"])   # 3 000 > 2 000 ; 1 000 <= 2 000

    def test_la_palette_est_celle_de_l_interface(self):
        canvas = FakeCanvas()
        ChartPainter(ChartPalette(mean="#123456")).draw(canvas, data())
        self.assertIn("#123456", [c[2].get("fill") for c in canvas.calls if c[0] == "create_line"])

    def test_sans_donnees_ou_trop_petit_ne_plante_pas(self):
        canvas = FakeCanvas()
        ChartPainter().draw(canvas, None)
        self.assertEqual(self.kinds(canvas), Counter({"create_text": 1}))
        small = FakeCanvas(100, 80)
        ChartPainter().draw(small, data())
        self.assertEqual(small.calls, [])

    def test_pas_de_graduation(self):
        self.assertEqual([nice_step(v) for v in (0.2, 1, 3, 7, 130, 2600, 9000)], [1, 1, 5, 10, 200, 5000, 10000])


if __name__ == "__main__":
    unittest.main()
