"""Boîtes de dialogue modales aux couleurs de la charte (customtkinter n'en fournit pas de toutes prêtes)."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog
from typing import Optional, Sequence

import customtkinter as ctk

from ..contract.interfaces import Dialogs
from . import theme as t
from .widgets import button, entry, label

# type : (couleur, pictogramme)
_KINDS = {"info": (t.BLUE, "i"), "warning": (t.AMBER, "!"), "error": (t.RED, "×"), "confirm": (t.GREEN, "?")}
_ALL = ("Tous les fichiers", "*.*")


class CtkDialogs(Dialogs):
    def __init__(self, root):
        self._root = root

    # ---- messages -------------------------------------------------------------------------------
    def info(self, title: str, message: str) -> None:
        self._message("info", title, message, ok="OK", cancel=None)

    def warning(self, title: str, message: str) -> None:
        self._message("warning", title, message, ok="OK", cancel=None)

    def error(self, title: str, message: str) -> None:
        self._message("error", title, message, ok="Fermer", cancel=None)

    def confirm(self, title: str, message: str) -> bool:
        return bool(self._message("confirm", title, message, ok="Confirmer", cancel="Annuler"))

    # ---- saisies --------------------------------------------------------------------------------
    def ask_text(self, title: str, prompt: str, initial: str = "") -> Optional[str]:
        return self._input(title, prompt, initial, validate=None)

    def ask_int(self, title: str, prompt: str, initial: int = 0, minimum: int = 0) -> Optional[int]:
        def validate(text: str):
            try:
                value = int(text.replace(" ", ""))
            except ValueError:
                return f"Entrez un nombre entier (≥ {minimum})."
            return None if value >= minimum else f"Entrez un nombre entier (≥ {minimum})."

        text = self._input(title, prompt, str(initial), validate)
        return None if text is None else int(text.replace(" ", ""))

    # ---- fichiers (boîtes natives du système) -------------------------------------------------------
    def ask_open_file(self, title: str, patterns: Sequence[str] = ()) -> Optional[str]:
        types = ([("Fichiers pris en charge", " ".join(patterns))] if patterns else []) + [_ALL]
        return filedialog.askopenfilename(title=title, filetypes=types, parent=self._root) or None

    def ask_save_file(self, title: str, initial_dir: str, initial_name: str) -> Optional[str]:
        extension = os.path.splitext(initial_name)[1]
        types = ([(f"Fichier {extension}", f"*{extension}")] if extension else []) + [_ALL]
        return filedialog.asksaveasfilename(
            title=title, initialdir=initial_dir, initialfile=initial_name, defaultextension=extension,
            filetypes=types, parent=self._root) or None

    # ---- mécanique des fenêtres modales ---------------------------------------------------------------
    def _window(self, title: str, width: int):
        win = ctk.CTkToplevel(self._root, fg_color=t.WHITE)
        win.title(title)
        win.resizable(False, False)
        win.transient(self._root)
        return win

    def _run(self, win, min_width: int) -> None:
        win.update_idletasks()
        width, height = max(win.winfo_reqwidth(), min_width), win.winfo_reqheight()
        x = self._root.winfo_rootx() + (self._root.winfo_width() - width) // 2
        y = self._root.winfo_rooty() + (self._root.winfo_height() - height) // 3
        win.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        win.wait_visibility()
        win.grab_set()
        win.focus_force()
        self._root.wait_window(win)

    def _header(self, win, kind: str, title: str):
        color, symbol = _KINDS[kind]
        strip = ctk.CTkFrame(win, height=5, fg_color=color, corner_radius=0)
        strip.pack(fill="x")
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(20, 6))
        ctk.CTkLabel(row, text=symbol, width=40, height=40, corner_radius=20, fg_color=color,
                     text_color=t.WHITE, font=t.font(20, "bold")).pack(side="left", padx=(0, 14))
        texts = ctk.CTkFrame(row, fg_color="transparent")
        texts.pack(side="left", fill="x", expand=True)
        label(texts, title, "strong").pack(anchor="w")
        return texts

    def _message(self, kind: str, title: str, message: str, ok: str, cancel: Optional[str]):
        win, result = self._window(title, 460), {"value": None}
        texts = self._header(win, kind, title)
        label(texts, message, "body", wraplength=360).pack(anchor="w", pady=(6, 0))
        buttons = ctk.CTkFrame(win, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(18, 20))

        def close(value):
            result["value"] = value
            win.destroy()

        primary = button(buttons, ok, lambda: close(True), "danger" if kind == "error" else "primary", width=110)
        primary.pack(side="right")
        if cancel:
            button(buttons, cancel, lambda: close(False), "secondary", width=110).pack(side="right", padx=(0, 10))
        win.bind("<Return>", lambda _e: close(True))
        win.bind("<Escape>", lambda _e: close(False))
        win.protocol("WM_DELETE_WINDOW", lambda: close(False))
        self._run(win, 460)
        return result["value"]

    def _input(self, title: str, prompt: str, initial: str, validate):
        win, result = self._window(title, 460), {"value": None}
        texts = self._header(win, "confirm", title)
        label(texts, prompt, "body", wraplength=360).pack(anchor="w", pady=(6, 8))
        value = tk.StringVar(value=initial)
        field_ = entry(texts, value, width=340)
        field_.pack(anchor="w")
        error = label(texts, "", "muted", color=t.RED)
        error.pack(anchor="w", pady=(4, 0))
        buttons = ctk.CTkFrame(win, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(14, 20))

        def accept():
            problem = validate(value.get()) if validate else None
            if problem:
                error.configure(text=problem)
                return
            result["value"] = value.get()
            win.destroy()

        def cancel():
            win.destroy()

        button(buttons, "OK", accept, "primary", width=110).pack(side="right")
        button(buttons, "Annuler", cancel, "secondary", width=110).pack(side="right", padx=(0, 10))
        win.bind("<Return>", lambda _e: accept())
        win.bind("<Escape>", lambda _e: cancel())
        win.protocol("WM_DELETE_WINDOW", cancel)
        win.after(150, lambda: (field_.focus_set(), field_.select_range(0, "end")))
        self._run(win, 460)
        return result["value"]
