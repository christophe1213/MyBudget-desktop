"""Graphique aux couleurs de la charte (vert Excel, moyenne en bleu, dépassement en orange)."""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from ..chart_painter import ChartPainter, ChartPalette
from ..contract.dto import ChartData
from ..dashboard_painter import DashboardPalette
from . import theme as t

PALETTE = ChartPalette(
    background=t.WHITE, bars=t.GREEN, over=t.AMBER, mean=t.BLUE, band=t.BLUE_LIGHT, band_legend="#BDD7F7",
    retained=t.RED, grid="#EDF2EF", axis="#9AA9A0", text=t.MUTED, legend_text=t.TEXT, empty_text=t.MUTED,
    font=t.FONT_FAMILY)


class ChartCanvas:
    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, height=250, background=t.WHITE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self._painter = ChartPainter(PALETTE)
        self._data: Optional[ChartData] = None
        self.canvas.bind("<Configure>", lambda _e: self.draw(self._data))

    def draw(self, data: Optional[ChartData]) -> None:
        self._data = data
        self._painter.draw(self.canvas, data)


DASHBOARD_PALETTE = DashboardPalette(
    background=t.WHITE, pie_border=t.WHITE, deposits=t.GREEN, expenses="#546E7A", grid="#EDF2EF",
    axis="#9AA9A0", text=t.MUTED, strong_text=t.TEXT, empty_text=t.MUTED, font=t.FONT_FAMILY)


class PainterCanvas:
    """Canevas redessiné à chaque redimensionnement par un dessinateur partagé (camembert ou courbes)."""

    def __init__(self, parent, painter, height: int = 260):
        self.canvas = tk.Canvas(parent, height=height, background=t.WHITE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=4)
        self._painter = painter
        self._data = None
        self.canvas.bind("<Configure>", lambda _e: self.draw(self._data))

    def draw(self, data) -> None:
        self._data = data
        self._painter.draw(self.canvas, data)
