from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Optional

from ...domain.model.errors import DomainError
from ...domain.model.ledger import Ledger
from ..dto import SyncExport, SyncReport, WalletSummary, WalletSyncResult, WalletSyncStatus
from ..errors import StorageError
from ..events import Event, EventEmitter
from ..ports.inbound import ManageWallets, SynchronizeData
from ..ports.outbound import Clock, LedgerRepository, SyncJournal
from ..repere_format import ledgers_to_repere
from ..repere_import import ReceivedWallet, new_transactions, repere_to_ledgers
from ..session import LedgerSession


class SyncUseCase(SynchronizeData):
    """Envoi : tous les portefeuilles lisibles. Réception : FUSION dans les portefeuilles du même nom
    (nouvelles transactions et catégories seulement : rien n'est supprimé, modifié ni dupliqué)."""

    def __init__(self, session: LedgerSession, wallets: ManageWallets, ledgers: LedgerRepository,
                 journal: SyncJournal, clock: Clock, events: EventEmitter):
        self._session = session
        self._wallets = wallets
        self._ledgers = ledgers
        self._journal = journal
        self._clock = clock
        self._events = events

    # ---- envoi ---------------------------------------------------------------------------------------
    def export_payload(self, start: Optional[dt.date]) -> SyncExport:
        items, skipped = [], []
        for summary in self._wallets.summaries():
            if summary.active:
                items.append((summary.name, self._session.ledger))
            elif summary.transaction_count is None:
                skipped.append(summary.name)
            else:
                try:
                    items.append((summary.name, self._ledgers.load(summary.location)))
                except StorageError:
                    skipped.append(summary.name)
        if not items:
            raise DomainError("Aucun portefeuille lisible à envoyer.")
        payload = ledgers_to_repere(items, active=self._wallets.active_name(), start=start,
                                    exported_at=self._clock.now())
        count = sum(len(w["transactions"]) for w in payload["wallets"])
        return SyncExport(payload, len(items), count, tuple(skipped))

    # ---- réception ---------------------------------------------------------------------------------
    def receive(self, payload) -> SyncReport:
        reception = repere_to_ledgers(payload)   # tout est validé avant de toucher à un portefeuille
        local = {s.name.casefold(): s for s in self._wallets.summaries()}
        results, other_wallet_changed = [], False
        for received in reception.wallets:
            target = local.get(received.name.casefold())
            if target is None:
                results.append(WalletSyncResult(received.name, WalletSyncStatus.UNKNOWN_WALLET))
                continue
            try:
                result = self._merge(target, received)
            except (DomainError, StorageError) as error:
                result = WalletSyncResult(received.name, WalletSyncStatus.FAILED, detail=str(error))
            other_wallet_changed |= result.status is WalletSyncStatus.MERGED and not target.active
            results.append(result)
        if other_wallet_changed:
            self._events.emit(Event.CATALOG_CHANGED)   # l'onglet Portefeuilles recompte les transactions
        return SyncReport(tuple(results), reception.warnings)

    def _merge(self, target: WalletSummary, received: ReceivedWallet) -> WalletSyncResult:
        if target.active:
            current = self._session.ledger
        elif target.transaction_count is None:
            raise StorageError("stockage introuvable ou illisible")
        else:
            current = self._ledgers.load(target.location)
        known = {c.casefold(): c for c in current.categories}   # « Bazar » reçu = « bazar » local
        incoming = Ledger([dataclasses.replace(t, category=known.get(t.category.casefold(), t.category))
                           for t in received.ledger.transactions])
        fresh = new_transactions(current, incoming)
        new_categories = [c for c in received.ledger.categories if c.casefold() not in known]
        already = len(incoming.transactions) - len(fresh)
        if not fresh and not new_categories:
            return WalletSyncResult(received.name, WalletSyncStatus.UNCHANGED, already_present=already)

        def mutate(ledger: Ledger) -> None:
            for category in new_categories:
                if not ledger.has_category(category):
                    ledger.add_category(category)
            ledger.merge(fresh)

        if target.active:
            self._session.apply(mutate, Event.DATA_IMPORTED)   # enregistre puis prévient l'interface
        else:
            updated = current.copy()
            mutate(updated)
            self._ledgers.save(target.location, updated)
        return WalletSyncResult(received.name, WalletSyncStatus.MERGED, added=len(fresh), already_present=already)

    # ---- journal -------------------------------------------------------------------------------------
    def record(self, kind: str, message: str) -> str:
        line = f"{self._clock.now():%Y-%m-%d %H:%M:%S} | {kind:<9} | {' '.join(message.split())}"
        try:
            self._journal.append(line)
        except StorageError:
            pass   # un journal impossible à écrire ne doit jamais faire échouer une synchronisation
        return line

    def recent_entries(self, count: int = 50) -> list[str]:
        try:
            return self._journal.tail(count)
        except StorageError:
            return []

    def journal_location(self) -> str:
        return self._journal.location
