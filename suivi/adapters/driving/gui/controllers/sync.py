from __future__ import annotations

import datetime as dt
import re
from typing import Sequence

from .....application.dto import SyncExport, SyncPreview, SyncReport, SyncWalletPreview, WalletSyncStatus
from .....application.ports.inbound import EventSource, SynchronizeData
from ... import sync_protocol as protocol
from ..contract.dto import Row
from ..contract.interfaces import Dialogs, SyncListener, SyncView
from ..formatting import format_ar, format_date
from ..parsing import InvalidInput, parse_date
from .base import Controller

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_ROWS = 2000   # lignes affichées dans la fenêtre de confirmation (le reste est quand même traité)


class SyncController(Controller, SyncListener):
    """Onglet « Synchronisation » : envoyer / récupérer des données et tenir le journal.

    RIEN ne part et RIEN n'est modifié sans confirmation : avant chaque envoi (voulu ou demandé par un appareil)
    et avant chaque réception, la liste exacte des données est affichée et l'utilisateur confirme ou annule.
    Chaque opération terminée est suivie d'une boîte de message.
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
            heading = f"Envoyer {export.transactions} transaction(s) ({self._period(start)}) aux appareils connectés ?"
            if not self._confirm_send(export, heading):
                self._log("ENVOI", "Envoi annulé par l'utilisateur : rien n'a été envoyé.")
                return
            reached = self._view.send(protocol.data_message(export.payload))
            if reached == 0:
                self._dialogs.warning("Envoi", "Aucun appareil n'a reçu les données (connexion perdue ?).")
                return
            text = self._describe(export, start, f"{reached} appareil(s)")
            self._log("ENVOI", text)
            self._dialogs.info("Envoi terminé", f"Données envoyées à {reached} appareil(s).\n\n{text}")

    def on_fetch(self) -> None:
        if not self._has_device():
            return
        reached = self._view.send(protocol.request_message())
        self._log("DEMANDE", f"Demande des données envoyée à {reached} appareil(s).")
        self._dialogs.info("Demande envoyée", f"Demande envoyée à {reached} appareil(s).\n\nLes données reçues seront "
                                              "affichées pour confirmation avant d'être ajoutées.")

    # ---- événements du réseau (déjà dans le thread de l'interface) -------------------------------------------
    def on_device_connected(self, client: int, address: str) -> None:
        self._log("CONNEXION", f"Appareil connecté : {address}")

    def on_device_disconnected(self, client: int, address: str) -> None:
        self._log("CONNEXION", f"Appareil déconnecté : {address}")

    def on_message(self, client: int, address: str, text: str) -> None:
        try:
            kind, body = protocol.parse(text)
        except protocol.MessageError as error:
            self._fail(client, address, str(error), notify=False)
            return
        if kind == "data":
            self._receive(client, address, body.get("payload"))
        elif kind == "request":
            self._answer_request(client, address, body)
        elif kind == "error":   # réponse de l'appareil à un envoi : refus ou échec de son côté
            self._log("ERREUR", f"{address} : {body.get('message', '')}")
            self._dialogs.warning("Réponse de l'appareil", f"{address} : {body.get('message', 'erreur')}")
        else:
            self._log("RECEPTION", f"{address} : {body.get('message', '')}")

    # ---- réception : aperçu -> confirmation -> fusion -> message --------------------------------------------
    def _receive(self, client: int, address: str, payload) -> None:
        try:
            preview = self._sync.preview_receive(payload)
            if preview.has_changes and not self._confirm_receive(address, preview):
                self._log("RECEPTION", f"{address} : réception refusée par l'utilisateur, rien n'a été modifié.")
                self._view.send(protocol.error_message("Réception refusée par l'utilisateur."), client)
                return
            report = self._sync.receive(payload)
        except Exception as error:  # noqa: BLE001  (donnée invalide ou stockage en échec : l'appareil est prévenu)
            self._fail(client, address, str(error))
            return
        summary = self._summarize(report)
        self._log("RECEPTION", f"{address} : {summary}")
        self._view.send(protocol.ack_message(summary), client)
        self._dialogs.info("Réception terminée", f"Données reçues de {address}.\n\n" + summary.replace(" ; ", "\n"))

    def _confirm_receive(self, address: str, preview: SyncPreview) -> bool:
        total = sum(len(w.transactions) for w in preview.wallets)
        notes = [self._receive_note(w) for w in preview.wallets]
        notes += [f"Attention : {w}" for w in preview.warnings]
        rows, hidden = self._rows(preview.wallets)
        if hidden:
            notes.append(f"{hidden} transaction(s) de plus ne sont pas affichées (elles seront ajoutées).")
        return self._view.confirm_transfer("Confirmer la réception", f"Ajouter {total} transaction(s) reçue(s) de "
                                           f"{address} à vos portefeuilles ?", notes, rows, "Ajouter")

    @staticmethod
    def _receive_note(wallet: SyncWalletPreview) -> str:
        if wallet.status is WalletSyncStatus.UNKNOWN_WALLET:
            return f"« {wallet.name} » : portefeuille inconnu sur ce PC, il sera ignoré."
        if wallet.status is WalletSyncStatus.FAILED:
            return f"« {wallet.name} » : lecture impossible ({wallet.detail}), il sera ignoré."
        text = f"« {wallet.name} » : {len(wallet.transactions)} nouvelle(s), {wallet.already_present} déjà présente(s)"
        return text + (f" ; catégories créées : {', '.join(wallet.new_categories)}" if wallet.new_categories else "")

    # ---- envoi : aperçu -> confirmation -> envoi -> message -------------------------------------------------
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
            heading = (f"{address} demande vos données : envoyer {export.transactions} transaction(s) "
                       f"({self._period(start)}) ?")
            if not self._confirm_send(export, heading):
                self._log("ENVOI", f"{address} : envoi refusé par l'utilisateur, rien n'a été envoyé.")
                self._view.send(protocol.error_message("Envoi refusé par l'utilisateur."), client)
                return
        except Exception as error:  # noqa: BLE001
            self._fail(client, address, str(error))
            return
        self._view.send(protocol.data_message(export.payload), client)
        text = self._describe(export, start, f"{address} (à sa demande)")
        self._log("ENVOI", text)
        self._dialogs.info("Envoi terminé", f"Données envoyées à {address}.\n\n{text}")

    def _confirm_send(self, export: SyncExport, heading: str) -> bool:
        notes = []
        for wallet in export.details:
            if wallet.opening_balances:
                balances = ", ".join(f"{name} {format_ar(amount)}" for name, amount in wallet.opening_balances)
                notes.append(f"« {wallet.name} » : opérations antérieures résumées dans les soldes de départ : {balances}.")
        if export.skipped:
            notes.append(f"Portefeuilles illisibles, non envoyés : {', '.join(export.skipped)}.")
        rows, hidden = self._rows(export.details)
        if hidden:
            notes.append(f"{hidden} transaction(s) de plus ne sont pas affichées (elles seront envoyées).")
        return self._view.confirm_transfer("Confirmer l'envoi", heading, notes, rows, "Envoyer")

    # ---- interne ---------------------------------------------------------------------------------------
    @staticmethod
    def _rows(wallets: Sequence[SyncWalletPreview]) -> tuple[list[Row], int]:
        """Les lignes du tableau de confirmation (au plus MAX_ROWS) et le nombre de lignes non affichées."""
        rows, total = [], 0
        for wallet in wallets:
            for t in wallet.transactions:
                total += 1
                if len(rows) < MAX_ROWS:
                    rows.append(Row(str(len(rows)), (wallet.name, format_date(t.date), t.category, t.label,
                                                     format_ar(t.signed_amount))))
        return rows, total - len(rows)

    def _fail(self, client: int, address: str, message: str, notify: bool = True) -> None:
        self._log("ERREUR", f"{address} : {message}")
        self._view.send(protocol.error_message(message), client)
        if notify:
            self._dialogs.warning("Synchronisation impossible", f"{address} : {message}")

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
    def _period(start) -> str:
        return f"depuis le {format_date(start)}" if start else "tout l'historique"

    def _describe(self, export: SyncExport, start, target: str) -> str:
        text = (f"{export.wallets} portefeuille(s), {export.transactions} transaction(s), "
                f"{self._period(start)} -> {target}")
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
