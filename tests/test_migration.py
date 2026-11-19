import datetime as dt
import tempfile
import unittest

from migrate_excel_to_sqlite import migrate
from suivi.adapters.driven.wiring import excel_ports, sqlite_ports
from suivi.domain.model.ledger import Ledger
from suivi.domain.model.transaction import Kind
from suivi.domain.model.wallet import WalletCatalog, WalletRef


class MigrationTest(unittest.TestCase):
    def test_excel_vers_sqlite_via_les_ports(self):
        folder = tempfile.mkdtemp()
        excel = excel_ports(folder)
        bank = Ledger(initial_balance=500, categories=["loyer"])
        bank.add_transaction(dt.date(2026, 9, 1), "loyer", Kind.EXPENSE, "septembre", 120000)
        excel.ledgers.save("transactions.xlsx", Ledger(categories=["riz"]))
        excel.ledgers.save("transactions_banque.xlsx", bank)
        excel.registry.save(WalletCatalog((WalletRef("Principal", "transactions.xlsx"),
                                           WalletRef("Banque", "transactions_banque.xlsx")), "Banque"))
        self.assertEqual(migrate(folder), 2)
        sqlite = sqlite_ports(folder)
        catalog = sqlite.registry.load()
        self.assertEqual((catalog.names, catalog.active), (["Principal", "Banque"], "Banque"))
        moved = sqlite.ledgers.load(catalog.find("Banque").location)
        self.assertEqual((moved.initial_balance, moved.transactions[0].amount), (500, 120000))


if __name__ == "__main__":
    unittest.main()
