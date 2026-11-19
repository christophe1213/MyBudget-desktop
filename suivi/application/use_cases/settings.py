from __future__ import annotations

from ...domain.model.errors import DomainError
from ..dto import ImportPreview
from ..events import Event
from ..ports.inbound import ManageLedger
from ..ports.outbound import FileOpener, LocationPolicy, TransactionImporter
from ..session import LedgerSession


class LedgerUseCase(ManageLedger):
    """Réglages du portefeuille ouvert : solde initial, import de transactions, accès au stockage."""

    def __init__(self, session: LedgerSession, importer: TransactionImporter, locations: LocationPolicy,
                 opener: FileOpener):
        self._session = session
        self._importer = importer
        self._locations = locations
        self._opener = opener

    def initial_balance(self) -> int:
        return self._session.ledger.initial_balance

    def set_initial_balance(self, amount: int) -> None:
        self._session.apply(lambda ledger: ledger.set_initial_balance(amount))

    def import_patterns(self) -> tuple:
        return tuple(self._importer.patterns)

    def preview_import(self, source: str) -> ImportPreview:
        transactions = tuple(self._importer.read(source))
        return ImportPreview(transactions, tuple(self._session.ledger.new_categories_in(transactions)))

    def import_transactions(self, preview: ImportPreview) -> None:
        self._session.apply(lambda ledger: ledger.merge(preview.transactions), Event.DATA_IMPORTED)

    def open_storage_file(self) -> None:
        path = self._locations.storage_path(self._session.ensure_saved())
        if path is None:
            raise DomainError("Ce type de stockage n'a pas de fichier à ouvrir.")
        self._opener.open(path)
