"""Adaptateurs « système » : ouverture de fichiers et horloge."""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys

from ...application.ports.outbound import Clock, FileOpener


class SystemFileOpener(FileOpener):
    """Ouvre un fichier avec l'application par défaut du système."""

    def open(self, path: str) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


class SystemClock(Clock):
    def today(self) -> dt.date:
        return dt.date.today()

    def now(self) -> dt.datetime:
        return dt.datetime.now()
