"""Charte graphique : vert Excel + fond blanc, avec quelques couleurs d'accompagnement.

Principale  : vert Excel (boutons, navigation, en-têtes de tableaux, graphique).
Neutres     : blanc, gris très clair (surfaces), gris-vert (bordures), texte presque noir.
Accompagnement : bleu (information, moyenne), ambre (avertissement, dépassement), rouge (suppression, erreur).
"""
from __future__ import annotations

from functools import lru_cache

import customtkinter as ctk

# --- principale -----------------------------------------------------------------------------
GREEN = "#217346"          # vert de l'icône Excel
GREEN_HOVER = "#1A5C38"
GREEN_LIGHT = "#E6F2EA"    # fond teinté (résumés, lignes de total)
GREEN_MID = "#C5E0CF"      # ligne sélectionnée
SIDEBAR_HOVER = "#2C8556"
SIDEBAR_MUTED = "#BFE0CC"

# --- neutres ----------------------------------------------------------------------------------
WHITE = "#FFFFFF"
SURFACE = "#F6F9F7"        # lignes alternées, zones secondaires
BORDER = "#DCE6E0"
TEXT = "#1E2A24"
MUTED = "#6B7B72"

# --- accompagnement ---------------------------------------------------------------------------
BLUE, BLUE_LIGHT = "#2B7DE9", "#E8F1FD"
AMBER, AMBER_LIGHT = "#F28C28", "#FFF1E0"
AMBER_DARK = "#B45309"     # texte sur fond ambre clair (lisible)
RED, RED_LIGHT = "#D64545", "#FDECEC"

FONT_FAMILY = "Segoe UI"


@lru_cache(maxsize=None)
def font(size: int = 13, weight: str = "normal"):
    """Police partagée (créée à la demande : une CTkFont exige qu'une fenêtre existe déjà)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
