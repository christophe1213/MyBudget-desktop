"""Boîtes de dialogue tkinter (implémentation de `Dialogs`)."""
from __future__ import annotations

import os
from tkinter import filedialog, messagebox, simpledialog
from typing import Optional, Sequence

from ..contract.interfaces import Dialogs

_ALL = ("Tous les fichiers", "*.*")


class TkDialogs(Dialogs):
    def __init__(self, root):
        self._root = root

    def info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self._root)

    def warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self._root)

    def error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self._root)

    def confirm(self, title: str, message: str) -> bool:
        return bool(messagebox.askyesno(title, message, parent=self._root))

    def ask_text(self, title: str, prompt: str, initial: str = "") -> Optional[str]:
        return simpledialog.askstring(title, prompt, initialvalue=initial, parent=self._root)

    def ask_int(self, title: str, prompt: str, initial: int = 0, minimum: int = 0) -> Optional[int]:
        return simpledialog.askinteger(title, prompt, initialvalue=initial, minvalue=minimum,
                                       parent=self._root)

    def ask_open_file(self, title: str, patterns: Sequence[str] = ()) -> Optional[str]:
        types = ([("Fichiers pris en charge", " ".join(patterns))] if patterns else []) + [_ALL]
        return filedialog.askopenfilename(title=title, filetypes=types, parent=self._root) or None

    def ask_save_file(self, title: str, initial_dir: str, initial_name: str) -> Optional[str]:
        extension = os.path.splitext(initial_name)[1]
        types = ([(f"Fichier {extension}", f"*{extension}")] if extension else []) + [_ALL]
        return filedialog.asksaveasfilename(
            title=title, initialdir=initial_dir, initialfile=initial_name,
            defaultextension=extension, filetypes=types, parent=self._root) or None
