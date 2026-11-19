"""Dessin du graphique des dépenses journalières sur un canevas (tkinter ou customtkinter).

Barres = dépense de chaque jour ; ligne = moyenne ; bande = ± 1 écart-type ; ligne en pointillés = budget
retenu (les jours qui le dépassent changent de couleur). Aucun import graphique : le canevas est fourni
par la vue, et la palette par la charte de chaque interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .contract.dto import ChartData
from .formatting import format_number


@dataclass(frozen=True)
class ChartPalette:
    background: str = "white"
    bars: str = "#4C78A8"
    over: str = "#F58518"
    mean: str = "#E45756"
    band: str = "#FBE3E3"
    band_legend: str = "#F4C7C7"
    retained: str = "#2CA02C"
    grid: str = "#E8E8E8"
    axis: str = "#888888"
    text: str = "#555555"
    legend_text: str = "#333333"
    empty_text: str = "#777777"
    font: str = "Arial"


def nice_step(value: float) -> int:
    """Plus petit pas « rond » (1, 2 ou 5 × 10^n) supérieur ou égal à `value`, au moins 1."""
    value = max(value, 1)
    power = 10 ** (len(str(int(value))) - 1)
    for m in (1, 2, 5, 10):
        if value <= m * power:
            return m * power
    return 10 * power


class ChartPainter:
    def __init__(self, palette: ChartPalette = ChartPalette()):
        self._p = palette

    def draw(self, c, data: Optional[ChartData]) -> None:
        p = self._p
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if data is None or not data.values:
            c.create_text(w / 2, h / 2, fill=p.empty_text, font=(p.font, 10),
                          text="Le graphique des dépenses journalières apparaîtra ici après l'analyse.")
            return
        if w < 150 or h < 120:
            return
        left, right, top, bottom = 72, 20, 34, 34
        zw, zh = w - left - right, h - top - bottom

        vmax = max(max(data.values), data.mean + data.std, data.retained or 0, 1)
        step = nice_step(vmax / 4)
        ymax = step * (int(vmax / step) + (1 if vmax % step else 0))

        def y(v: float) -> float:
            return top + zh - v / ymax * zh

        for k in range(int(ymax / step) + 1):  # grille et graduations
            v = k * step
            c.create_line(left, y(v), left + zw, y(v), fill=p.grid)
            c.create_text(left - 8, y(v), text=format_number(v), anchor="e", font=(p.font, 8), fill=p.text)

        c.create_rectangle(left, y(data.mean + data.std), left + zw, y(max(0, data.mean - data.std)),
                           fill=p.band, outline="")
        n = len(data.values)
        bar = zw / n
        for i, v in enumerate(data.values):
            if v > 0:
                color = p.over if (data.retained is not None and v > data.retained) else p.bars
                c.create_rectangle(left + i * bar + bar * 0.15, y(v), left + (i + 1) * bar - bar * 0.15,
                                   y(0), fill=color, outline="")
        c.create_line(left, y(data.mean), left + zw, y(data.mean), fill=p.mean, width=2)
        if data.retained is not None:
            c.create_line(left, y(data.retained), left + zw, y(data.retained), fill=p.retained, width=2,
                          dash=(6, 3))
        c.create_line(left, top, left, top + zh, fill=p.axis)
        c.create_line(left, top + zh, left + zw, top + zh, fill=p.axis)
        for i in sorted({0, n // 2, n - 1}):  # dates sur l'axe horizontal
            c.create_text(left + (i + 0.5) * bar, top + zh + 15, text=data.labels[i],
                          font=(p.font, 8), fill=p.text)

        legend = [(p.bars, "dépense du jour"), (p.mean, data.mean_text), (p.band_legend, "± 1 écart-type")]
        if data.retained_text:
            legend.append((p.retained, data.retained_text))
        x = left
        for color, text in legend:
            c.create_rectangle(x, 11, x + 10, 21, fill=color, outline="")
            item = c.create_text(x + 15, 16, text=text, anchor="w", font=(p.font, 8), fill=p.legend_text)
            x = c.bbox(item)[2] + 16
