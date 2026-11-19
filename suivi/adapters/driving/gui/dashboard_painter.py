"""Dessin des deux graphiques du tableau de bord sur un canevas (tkinter ou customtkinter).

- `PiePainter`  : camembert + légende (nom, montant, pourcentage) ;
- `FlowPainter` : courbes des entrées et des sorties par jour, avec valeurs et dates.
Aucun import graphique : le canevas vient de la vue, la palette de la charte de chaque interface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .chart_painter import nice_step
from .contract.dto import FlowChartData, PieData
from .formatting import format_number

_PIE_COLORS = ("#217346", "#7F9C8A", "#94A7B5", "#BAD6C6", "#16553A", "#4F8A6B", "#C9D6CF", "#5B7083",
               "#A3C9B1", "#2E5E4E")


@dataclass(frozen=True)
class DashboardPalette:
    background: str = "white"
    pie_colors: tuple = _PIE_COLORS
    pie_border: str = "white"
    deposits: str = "#217346"
    expenses: str = "#546E7A"
    grid: str = "#E8EDEA"
    axis: str = "#9AA9A0"
    text: str = "#6B7B72"
    strong_text: str = "#1E2A24"
    empty_text: str = "#6B7B72"
    font: str = "Arial"


class PiePainter:
    def __init__(self, palette: DashboardPalette = DashboardPalette()):
        self._p = palette

    def draw(self, c, data: Optional[PieData]) -> None:
        p = self._p
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if data is None or not data.slices:
            c.create_text(w / 2, h / 2, fill=p.empty_text, font=(p.font, 10),
                          text="Aucun solde positif à répartir pour le moment.")
            return
        if w < 200 or h < 140:
            return
        total = sum(s.value for s in data.slices)
        pad = 16
        size = min(h - 2 * pad, w * 0.46)
        left, top = pad, (h - size) / 2
        box = (left, top, left + size, top + size)
        if len(data.slices) == 1:   # un seul budget : disque plein (un arc de 360° ne se dessine pas)
            c.create_oval(*box, fill=p.pie_colors[0], outline=p.pie_border, width=2)
        else:
            start = 90.0            # on part du haut et on tourne dans le sens des aiguilles d'une montre
            for i, s in enumerate(data.slices):
                extent = -360.0 * s.value / total
                c.create_arc(*box, start=start, extent=extent, fill=p.pie_colors[i % len(p.pie_colors)],
                             outline=p.pie_border, width=2)
                start += extent
        row = min(46.0, (h - 2 * pad) / len(data.slices))
        x = box[2] + 34
        y = h / 2 - row * len(data.slices) / 2 + row / 2
        for i, s in enumerate(data.slices):
            c.create_rectangle(x, y - 14, x + 10, y - 4, fill=p.pie_colors[i % len(p.pie_colors)], outline="")
            c.create_text(x + 18, y - 9, text=s.label, anchor="w", font=(p.font, 10, "bold"), fill=p.strong_text)
            c.create_text(x + 18, y + 7, text=f"{s.amount_text} · {s.percent_text}", anchor="w",
                          font=(p.font, 9), fill=p.text)
            y += row


class FlowPainter:
    MAX_VALUE_LABELS = 15     # au-delà, on n'écrit plus les valeurs sur les points (illisible)
    MAX_DATE_LABELS = 8

    def __init__(self, palette: DashboardPalette = DashboardPalette()):
        self._p = palette

    def draw(self, c, data: Optional[FlowChartData]) -> None:
        p = self._p
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if data is None or not data.labels:
            c.create_text(w / 2, h / 2, fill=p.empty_text, font=(p.font, 10),
                          text="Aucune donnée pour cette période.")
            return
        if w < 220 or h < 140:
            return
        left, right, top, bottom = 56, 28, 44, 34
        zw, zh = w - left - right, h - top - bottom
        n = len(data.labels)
        vmax = max(max(data.deposits), max(data.expenses), 1)
        step = nice_step(vmax / 4)
        ymax = step * (int(vmax / step) + (1 if vmax % step else 0))

        def y(v: float) -> float:
            return top + zh - v / ymax * zh

        def x(i: int) -> float:
            return left + zw / 2 if n == 1 else left + i * zw / (n - 1)

        for k in range(int(ymax / step) + 1):           # grille et graduations
            v = k * step
            c.create_line(left, y(v), left + zw, y(v), fill=p.grid)
            c.create_text(left - 10, y(v), text=format_number(v), anchor="e", font=(p.font, 8), fill=p.text)
        c.create_line(left, y(0), left + zw, y(0), fill=p.axis)

        label_every = max(1, math.ceil(n / self.MAX_DATE_LABELS))   # dates : environ 8 au plus
        for i in range(n):
            if i % label_every == 0 or i == n - 1:
                c.create_text(x(i), top + zh + 16, text=data.labels[i], font=(p.font, 8), fill=p.text)

        for values, color in ((data.deposits, p.deposits), (data.expenses, p.expenses)):
            points = [(x(i), y(v)) for i, v in enumerate(values)]
            if n > 1:
                c.create_line(*[coord for pt in points for coord in pt], fill=color, width=2)
            for px, py in points:
                c.create_oval(px - 3, py - 3, px + 3, py + 3, fill=p.background, outline=color, width=2)

        if n <= self.MAX_VALUE_LABELS:                   # valeurs au-dessus des points (une seule fois si égales)
            for i in range(n):
                shown = {data.expenses[i], data.deposits[i]}
                for value in sorted(shown, reverse=True):
                    c.create_text(x(i), y(value) - 11, text=format_number(value), font=(p.font, 8),
                                  fill=p.strong_text)

        lx = left
        for color, text in ((p.deposits, data.deposits_text), (p.expenses, data.expenses_text)):
            c.create_line(lx, 18, lx + 22, 18, fill=color, width=3)
            item = c.create_text(lx + 30, 18, text=text, anchor="w", font=(p.font, 9), fill=p.strong_text)
            lx = c.bbox(item)[2] + 26
