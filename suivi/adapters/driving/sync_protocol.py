"""Messages JSON échangés avec un appareil à travers le WebSocket (un message = un texte JSON).

    appareil -> PC   {"type": "data", "payload": {...format « repere »...}}   envoie ses données au PC
    appareil -> PC   {"type": "request", "start": "AAAA-MM-JJ"}               demande les données du PC (date facultative)
    PC -> appareil   {"type": "data", "payload": {...}}                       envoie les données du PC
    PC -> appareil   {"type": "request"}                                      demande à l'appareil d'envoyer ses données
    dans les deux sens {"type": "ack", "message": "..."} ou {"type": "error", "message": "..."}   réponse à un « data »
"""
from __future__ import annotations

import json

KINDS = ("data", "request", "ack", "error")


class MessageError(ValueError):
    """Message reçu illisible ou de type inconnu (le texte est destiné à l'utilisateur)."""


def data_message(payload: dict) -> str:
    return json.dumps({"type": "data", "payload": payload}, ensure_ascii=False)


def request_message() -> str:
    return json.dumps({"type": "request"})


def ack_message(text: str) -> str:
    return json.dumps({"type": "ack", "message": text}, ensure_ascii=False)


def error_message(text: str) -> str:
    return json.dumps({"type": "error", "message": text}, ensure_ascii=False)


def parse(text: str) -> tuple[str, dict]:
    """(type, message complet) ; lève MessageError si le texte n'est pas un message valide."""
    try:
        message = json.loads(text)
    except ValueError:
        raise MessageError("Message illisible (JSON invalide).") from None
    if not isinstance(message, dict) or message.get("type") not in KINDS:
        raise MessageError("Type de message inconnu.")
    return message["type"], message
