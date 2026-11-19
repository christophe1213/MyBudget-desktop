"""Page « Analyse budget » : statistiques, budgets proposés et graphique."""
from __future__ import annotations

from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.dto import ChartData, Row
from ..contract.interfaces import AnalysisListener, AnalysisView
from . import theme as t
from .chart import ChartCanvas
from .widgets import Column, Table, button, call, card, combo, entry, field, label, tinted

# (clé utilisée par le contrôleur, libellé affiché)
SUGGESTIONS = [("serre", "Serré — la moyenne"),
               ("equilibre", "Équilibré — moyenne + ½ écart-type"),
               ("confortable", "Confortable — moyenne + 1 écart-type")]


class CtkAnalysisView(AnalysisView):
    def __init__(self, parent):
        self._listener: Optional[AnalysisListener] = None
        self._category = ctk.StringVar()
        self._start = ctk.StringVar()
        self._end = ctk.StringVar()
        self._budget = ctk.StringVar()

        top = card(parent)
        top.pack(fill="x")
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=14)
        column = field(row, "Catégorie")
        column.pack(side="left", padx=(0, 14))
        self._combo = combo(column, self._category, 180, lambda _c: call(self._get, "on_category_changed"))
        self._combo.pack(anchor="w")
        for caption, var in (("Du (JJ/MM/AAAA)", self._start), ("Au (inclus)", self._end)):
            column = field(row, caption)
            column.pack(side="left", padx=(0, 14))
            entry(column, var, 130).pack(anchor="w")
        button(row, "Analyser", lambda: call(self._get, "on_analyze"), "primary", 120).pack(
            side="left", pady=(22, 0))

        middle = ctk.CTkFrame(parent, fg_color="transparent")
        middle.pack(fill="x", pady=14)
        left = ctk.CTkFrame(middle, fg_color="transparent", width=380)
        left.pack(side="left", fill="y")
        self._stats = Table(left, [Column("name", "Indicateur", 230), Column("value", "Valeur", 140, "e")], height=8)

        right = card(middle)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        label(right, "Budget journalier proposé", "section").pack(anchor="w", padx=18, pady=(14, 6))
        self._suggestion_labels = {}
        for key, title in SUGGESTIONS:
            line = ctk.CTkFrame(right, fg_color="transparent")
            line.pack(fill="x", padx=18, pady=2)
            label(line, title, "body", width=270).pack(side="left")
            self._suggestion_labels[key] = label(line, "—", "strong", width=110, anchor="e")
            self._suggestion_labels[key].pack(side="left")
            button(line, "Utiliser", lambda k=key: call(self._get, "on_use_suggestion", k), "secondary", 90).pack(
                side="left", padx=(10, 0))
        note = tinted(right, t.BLUE_LIGHT)
        note.pack(fill="x", padx=18, pady=(10, 8))
        self._diagnostic = label(note, "", "body", wraplength=560)
        self._diagnostic.pack(anchor="w", padx=12, pady=8)

        entry_line = ctk.CTkFrame(right, fg_color="transparent")
        entry_line.pack(fill="x", padx=18, pady=(0, 4))
        label(entry_line, "Budget / jour retenu (Ar)", "strong").pack(side="left", padx=(0, 10))
        entry(entry_line, self._budget, 120).pack(side="left")
        button(entry_line, "Enregistrer comme budget / jour", lambda: call(self._get, "on_save_budget"),
               "primary").pack(side="left", padx=10)
        self._current = label(right, "", "muted")
        self._current.pack(anchor="w", padx=18, pady=(0, 12))

        chart_card = card(parent)
        chart_card.pack(fill="both", expand=True)
        self._chart = ChartCanvas(chart_card)
        self._budget.trace_add("write", lambda *_: call(self._get, "on_budget_edited"))

    def _get(self):
        return self._listener

    def set_listener(self, listener: AnalysisListener) -> None:
        self._listener = listener

    def set_categories(self, categories: Sequence[str]) -> None:
        self._combo.configure(values=list(categories))

    def get_category(self) -> str:
        return self._category.get()

    def set_category(self, name: str) -> None:
        self._category.set(name)

    def get_period(self) -> tuple[str, str]:
        return self._start.get(), self._end.get()

    def set_period(self, start: str, end: str) -> None:
        self._start.set(start)
        self._end.set(end)

    def show_stats(self, rows: Sequence[Row]) -> None:
        self._stats.show(rows)

    def show_suggestions(self, texts: dict) -> None:
        for key, lbl in self._suggestion_labels.items():
            lbl.configure(text=texts.get(key, "—"))

    def show_diagnostic(self, text: str) -> None:
        self._diagnostic.configure(text=text)

    def get_budget_text(self) -> str:
        return self._budget.get()

    def set_budget_text(self, text: str) -> None:
        self._budget.set(text)

    def show_current_budget(self, text: str) -> None:
        self._current.configure(text=text)

    def draw_chart(self, data: Optional[ChartData]) -> None:
        self._chart.draw(data)
