"""Composants de l'interface customtkinter : cartes, boutons, champs, tableau (une seule charte)."""
from __future__ import annotations

from tkinter import ttk
from typing import Callable, Optional, Sequence

import customtkinter as ctk

from ..contract.dto import Row
from ..view_support import call  # noqa: F401  (réexporté pour les vues)
from . import theme as t

_LABELS = {  # type : (taille, graisse, couleur)
    "body": (13, "normal", t.TEXT), "strong": (13, "bold", t.TEXT), "muted": (12, "normal", t.MUTED),
    "section": (15, "bold", t.GREEN), "title": (26, "bold", t.TEXT), "kpi": (13, "normal", t.TEXT),
    "heading": (16, "bold", t.TEXT),
}


def card(parent, fg: str = t.WHITE, border: bool = True) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=fg, corner_radius=12, border_width=1 if border else 0,
                        border_color=t.BORDER)


def tinted(parent, color: str = t.GREEN_LIGHT) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=color, corner_radius=10, border_width=0)


def label(parent, text: str = "", kind: str = "body", color: Optional[str] = None, **options) -> ctk.CTkLabel:
    size, weight, default = _LABELS[kind]
    options = {"anchor": "w", "justify": "left", **options}   # l'appelant peut surcharger l'alignement
    return ctk.CTkLabel(parent, text=text, font=t.font(size, weight), text_color=color or default, **options)


def button(parent, text: str, command: Callable[[], None], kind: str = "primary",
           width: Optional[int] = None) -> ctk.CTkButton:
    styles = {
        "primary": dict(fg_color=t.GREEN, hover_color=t.GREEN_HOVER, text_color=t.WHITE, border_width=0),
        "secondary": dict(fg_color=t.WHITE, hover_color=t.GREEN_LIGHT, text_color=t.GREEN, border_width=1,
                          border_color=t.GREEN),
        "danger": dict(fg_color=t.WHITE, hover_color=t.RED_LIGHT, text_color=t.RED, border_width=1,
                       border_color=t.RED),
    }
    options = dict(text=text, command=command, height=36, corner_radius=8, font=t.font(13, "bold"),
                   **styles[kind])
    if width:
        options["width"] = width
    return ctk.CTkButton(parent, **options)


def entry(parent, variable, width: int = 140) -> ctk.CTkEntry:
    return ctk.CTkEntry(parent, textvariable=variable, width=width, height=36, corner_radius=8, border_width=1,
                        border_color=t.BORDER, fg_color=t.WHITE, text_color=t.TEXT, font=t.font(13))


def combo(parent, variable, width: int = 170, command: Optional[Callable[[str], None]] = None,
          values: Sequence[str] = ()) -> ctk.CTkComboBox:
    return ctk.CTkComboBox(
        parent, variable=variable, values=list(values), width=width, height=36, corner_radius=8, border_width=1,
        border_color=t.BORDER, fg_color=t.WHITE, text_color=t.TEXT, button_color=t.GREEN,
        button_hover_color=t.GREEN_HOVER, dropdown_fg_color=t.WHITE, dropdown_hover_color=t.GREEN_LIGHT,
        dropdown_text_color=t.TEXT, font=t.font(13), dropdown_font=t.font(13), state="readonly", command=command)


def segmented(parent, variable, values: Sequence[str], width: int = 200) -> ctk.CTkSegmentedButton:
    return ctk.CTkSegmentedButton(
        parent, values=list(values), variable=variable, width=width, height=36, corner_radius=8,
        fg_color=t.SURFACE, selected_color=t.GREEN, selected_hover_color=t.GREEN_HOVER,
        unselected_color=t.SURFACE, unselected_hover_color=t.GREEN_LIGHT, text_color=t.TEXT,
        font=t.font(13, "bold"))


def field(parent, caption: str) -> ctk.CTkFrame:
    """Colonne « légende au-dessus, champ en dessous » : créer le champ avec ce cadre pour parent."""
    column = ctk.CTkFrame(parent, fg_color="transparent")
    label(column, caption, "muted").pack(anchor="w", pady=(0, 4))
    return column


def apply_table_style() -> None:
    """Style des tableaux (ttk.Treeview) pour qu'ils suivent la charte ; à appeler une fois la fenêtre créée."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Suivi.Treeview", background=t.WHITE, fieldbackground=t.WHITE, foreground=t.TEXT,
                    rowheight=32, borderwidth=0, font=(t.FONT_FAMILY, 10))
    style.configure("Suivi.Treeview.Heading", background=t.GREEN, foreground=t.WHITE, relief="flat",
                    borderwidth=0, font=(t.FONT_FAMILY, 10, "bold"), padding=(10, 8))
    style.map("Suivi.Treeview.Heading", background=[("active", t.GREEN_HOVER)])
    style.map("Suivi.Treeview", background=[("selected", t.GREEN_MID)], foreground=[("selected", t.TEXT)])
    style.layout("Suivi.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


class Column:
    def __init__(self, id: str, title: str, width: int, anchor: str = "w"):
        self.id, self.title, self.width, self.anchor = id, title, width, anchor


class Table:
    """Tableau aux lignes alternées, dans un cadre arrondi, avec barre de défilement."""

    def __init__(self, parent, columns: Sequence[Column], height: Optional[int] = None):
        frame = ctk.CTkFrame(parent, fg_color=t.WHITE, corner_radius=10, border_width=1, border_color=t.BORDER)
        frame.pack(fill="both", expand=True)
        options = {"height": height} if height else {}
        self.tree = ttk.Treeview(frame, columns=[c.id for c in columns], show="headings",
                                 style="Suivi.Treeview", **options)
        for c in columns:
            self.tree.heading(c.id, text=c.title, anchor=c.anchor)
            self.tree.column(c.id, width=c.width, anchor=c.anchor)
        self.tree.tag_configure("odd", background=t.SURFACE)
        self.tree.tag_configure("emphasis", background=t.GREEN_LIGHT, font=(t.FONT_FAMILY, 10, "bold"))
        scrollbar = ctk.CTkScrollbar(frame, command=self.tree.yview, button_color=t.GREEN_MID,
                                     button_hover_color=t.GREEN)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        scrollbar.pack(side="right", fill="y", padx=2, pady=2)

    def show(self, rows: Sequence[Row], selected_id: Optional[str] = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            tags = ("emphasis",) if row.emphasis else (("odd",) if i % 2 else ())
            self.tree.insert("", "end", iid=row.id, values=row.values, tags=tags)
        if selected_id is not None and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)

    def selected_ids(self) -> list[str]:
        return list(self.tree.selection())

    def selected_id(self) -> Optional[str]:
        ids = self.selected_ids()
        return ids[0] if ids else None

    def on_double_click(self, callback: Callable[[], None]) -> None:
        self.tree.bind("<Double-1>", lambda _event: callback())
