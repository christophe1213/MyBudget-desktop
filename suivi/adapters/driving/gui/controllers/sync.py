from __future__ import annotations

import datetime as dt
import re

from .....application.dto import SyncExport, SyncReport, WalletSyncStatus
from .....application.ports.inbound import EventSource, SynchronizeData
from ... import sync_protocol as protocol
from ..contract.interfaces import Dialogs, SyncListener, SyncView
from ..formatting import format_date
from ..parsing import InvalidInput, parse_date
from .base import Controller

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SyncController(Controller, SyncListener):
    """Onglet « Synchronisation » : envoyer / récupérer des données et tenir le journal.

    Les messages d'un appareil sont traités ici, jamais en dialogue modal : une erreur est écrite au journal
    et renvoyée à l'appareil, l'utilisateur du PC n'est interrompu que par ses propres actions.
    """

    def __init__(self, events: EventSource, dialogs: Dialogs, view: SyncView, sync: SynchronizeData):
        super().__init__(events, dialogs)
        self._view = view
        self._sync = sync
        view.set_listener(self)

    def refresh(self) -> None:
        self._view.show_journal(self._sync.recent_entries(), self._sync.journal_location())

    # le journal ne dépend pas du portefeuille ouvert : on ne le recharge pas à chaque changement de données
    def on_wallet_changed(self) -> None: ...

    def on_data_changed(self) -> None: ...

    def on_imported(self) -> None: ...

    # ---- actions de l'utilisateur ----------------------------------------------------------------------
    def on_send(self) -> None:
        if not self._has_device():
            return
        with self.guard("Envoi"):
            start = self._start_date()
            export = self._sync.export_payload(start)
            reached = self._view.send(protocol.data_message(export.payload))
            if reached == 0:
                self._dialogs.warning("Envoi", "Aucun appareil n'a reçu les données (connexion perdue ?).")
                return
            self._log("ENVOI", self._describe(export, start, f"{reached} appareil(s)"))

    def on_fetch(self) -> None:
        if not self._has_device():
            return
        reached = self._view.send(protocol.request_message())
        self._log("DEMANDE", f"Demande des données envoyée à {reached} appareil(s).")

    # ---- événements du réseau (déjà dans le thread de l'interface) -------------------------------------------
    def on_device_connected(self, client: int, address: str) -> None:
        self._log("CONNEXION", f"Appareil connecté : {address}")

    def on_device_disconnected(self, client: int, address: str) -> None:
        self._log("CONNEXION", f"Appareil déconnecté : {address}")

    def on_message(self, client: int, address: str, text: str) -> None:
        try:
            kind, body = protocol.parse(text)
        except protocol.MessageError as error:
            self._fail(client, address, str(error))
            return
        if kind == "data":
            self._receive(client, address, body.get("payload"))
        elif kind == "request":
            self._answer_request(client, address, body)
        else:   # « ack » ou « error » : réponse de l'appareil à un envoi
            self._log("ERREUR" if kind == "error" else "RECEPTION", f"{address} : {body.get('message', '')}")

    # ---- interne ---------------------------------------------------------------------------------------
    def _receive(self, client: int, address: str, payload) -> None:
        try:
            report = self._sync.receive(payload)
        except Exception as error:  # noqa: BLE001  (donnée invalide ou stockage en échec : l'appareil est prévenu)
            self._fail(client, address, str(error))
            return
        summary = self._summarize(report)
        self._log("RECEPTION", f"{address} : {summary}")
        self._view.send(protocol.ack_message(summary), client)

    def _answer_request(self, client: int, address: str, body: dict) -> None:
        try:
            raw = body.get("start")
            if raw in (None, ""):
                start = self._start_date()
            elif isinstance(raw, str) and _ISO_DATE.match(raw):
                start = dt.date.fromisoformat(raw)
            else:
                raise InvalidInput("Date de début invalide (format AAAA-MM-JJ attendu).")
            export = self._sync.export_payload(start)
        except Exception as error:  # noqa: BLE001
            self._fail(client, address, str(error))
            return
        self._view.send(protocol.data_message(export.payload), client)
        self._log("ENVOI", self._describe(export, start, f"{address} (à sa demande)"))

    def _fail(self, client: int, address: str, message: str) -> None:
        self._log("ERREUR", f"{address} : {message}")
        self._view.send(protocol.error_message(message), client)

    def _has_device(self) -> bool:
        if self._view.device_count() > 0:
            return True
        self._dialogs.info("Synchronisation", "Aucun appareil connecté.\nDémarrez le serveur, puis flashez le QR code "
                                              "avec l'appareil (même réseau Wi-Fi).")
        return False

    def _start_date(self):
        text = self._view.start_date_text().strip()
        return parse_date(text) if text else None

    def _log(self, kind: str, message: str) -> None:
        self._view.show_message(self._sync.record(kind, message))

    @staticmethod
    def _describe(export: SyncExport, start, target: str) -> str:
        period = f"depuis le {format_date(start)}" if start else "tout l'historique"
        text = f"{export.wallets} portefeuille(s), {export.transactions} transaction(s), {period} -> {target}"
        return text + (f" (non lus : {', '.join(export.skipped)})" if export.skipped else "")

    @staticmethod
    def _summarize(report: SyncReport) -> str:
        parts = []
        for r in report.results:
            if r.status is WalletSyncStatus.MERGED:
                parts.append(f"{r.name} : {r.added} ajoutée(s), {r.already_present} déjà présente(s)")
            elif r.status is WalletSyncStatus.FAILED:
                parts.append(f"{r.name} : échec ({r.detail})")
            else:
                parts.append(f"{r.name} : {r.status.value}")
        return " ; ".join(parts) + ("".join(f" ATTENTION : {w}" for w in report.warnings))
