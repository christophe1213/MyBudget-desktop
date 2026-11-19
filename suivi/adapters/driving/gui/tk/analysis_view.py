"""Onglet « Analyse budget » : statistiques, budgets proposés et graphique."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence

from ..contract.dto import ChartData, Row
from ..contract.interfaces import AnalysisListener, AnalysisView
from .chart import ChartCanvas
from .widgets import Column, Table, call

# (clé utilisée par le contrôleur, libellé affiché)
SUGGESTIONS = [("serre", "Serré — la moyenne"),
               ("equilibre", "Équilibré — moyenne + ½ écart-type"),
               ("confortable", "Confortable — moyenne + 1 écart-type")]


class TkAnalysisView(AnalysisView):
    def __init__(self, parent):
        self._listener: Optional[AnalysisListener] = None
        self._category = tk.StringVar()
        self._start = tk.StringVar()
        self._end = tk.StringVar()
        self._budget = tk.StringVar()

        top = ttk.LabelFrame(parent, text="Dépenses à analyser", padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Catégorie").pack(side="left")
        self._combo = ttk.Combobox(top, textvariable=self._category, width=16, state="readonly")
        self._combo.pack(side="left", padx=(4, 12))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: call(self._get, "on_category_changed"))
        ttk.Label(top, text="Du").pack(side="left")
        ttk.Entry(top, textvariable=self._start, width=12).pack(side="left", padx=(4, 8))
        ttk.Label(top, text="au").pack(side="left")
        ttk.Entry(top, textvariable=self._end, width=12).pack(side="left", padx=(4, 12))
        ttk.Button(top, text="Analyser", command=lambda: call(self._get, "on_analyze")).pack(side="left")

        middle = ttk.Frame(parent)
        middle.pack(fill="x", pady=(8, 0))
        left = ttk.Frame(middle)
        left.pack(side="left", fill="y")
        self._stats = Table(left, [Column("name", "Indicateur", 210), Column("value", "Valeur", 130, "e")],
                            height=10)

        right = ttk.LabelFrame(middle, text="Budget journalier proposé", padding=10)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self._suggestion_labels = {}
        for key, title in SUGGESTIONS:
            line = ttk.Frame(right)
            line.pack(fill="x", pady=1)
            ttk.Label(line, text=title, width=38).pack(side="left")
            self._suggestion_labels[key] = ttk.Label(line, text="—", width=12, anchor="e")
            self._suggestion_labels[key].pack(side="left")
            ttk.Button(line, text="Utiliser",
                       command=lambda k=key: call(self._get, "on_use_suggestion", k)).pack(side="left", padx=6)
        self._diagnostic = ttk.Label(right, text="", wraplength=430, justify="left", foreground="#333")
        self._diagnostic.pack(anchor="w", pady=(8, 6))

        entry_line = ttk.Frame(right)
        entry_line.pack(fill="x")
        ttk.Label(entry_line, text="Budget / jour retenu (Ar) :", font=("Arial", 10, "bold")).pack(side="left")
        ttk.Entry(entry_line, textvariable=self._budget, width=10).pack(side="left", padx=6)
        ttk.Button(entry_line, text="Enregistrer comme budget / jour",
                   command=lambda: call(self._get, "on_save_budget")).pack(side="left")
        self._current = ttk.Label(right, text="", foreground="#555")
        self._current.pack(anchor="w", pady=(6, 0))

        self._chart = ChartCanvas(parent)
        self._budget.trace_add("write", lambda *_: call(self._get, "on_budget_edited"))

    def _get(self):
        return self._listener

    def set_listener(self, listener: AnalysisListener) -> None:
        self._listener = listener

    def set_categories(self, categories: Sequence[str]) -> None:
        self._combo["values"] = list(categories)

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
        for key, label in self._suggestion_labels.items():
            label.config(text=texts.get(key, "—"))

    def show_diagnostic(self, text: str) -> None:
        self._diagnostic.config(text=text)

    def get_budget_text(self) -> str:
        return self._budget.get()

    def set_budget_text(self, text: str) -> None:
        self._budget.set(text)

    def show_current_budget(self, text: str) -> None:
        self._current.config(text=text)

    def draw_chart(self, data: Optional[ChartData]) -> None:
        self._chart.draw(data)
