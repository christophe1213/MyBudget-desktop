"""Graphique de l'interface tkinter classique : un Canvas + le dessinateur partagé."""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from ..chart_painter import ChartPainter
from ..contract.dto import ChartData


class ChartCanvas:
    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, height=240, background="white", highlightthickness=1,
                                highlightbackground="#CCCCCC")
        self.canvas.pack(fill="both", expand=True, pady=(10, 0))
        self._painter = ChartPainter()
        self._data: Optional[ChartData] = None
        self.canvas.bind("<Configure>", lambda _e: self.draw(self._data))

    def draw(self, data: Optional[ChartData]) -> None:
        self._data = data
        self._painter.draw(self.canvas, data)


class PainterCanvas:
    """Canevas redessiné à chaque redimensionnement par un dessinateur partagé (camembert ou courbes)."""

    def __init__(self, parent, painter, height: int = 260):
        self.canvas = tk.Canvas(parent, height=height, background="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=4)
        self._painter = painter
        self._data = None
        self.canvas.bind("<Configure>", lambda _e: self.draw(self._data))

    def draw(self, data) -> None:
        self._data = data
        self._painter.draw(self.canvas, data)
