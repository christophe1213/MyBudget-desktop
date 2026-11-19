"""Copie tous les portefeuilles Excel (portefeuilles.txt + classeurs) vers la base SQLite suivi.db.

    python migrate_excel_to_sqlite.py

Ne supprime rien. Sert aussi d'exemple : migrer d'un stockage à l'autre ne demande que les PORTS
(aucun code d'interface ni de calcul n'est concerné).
"""
import os

from suivi.adapters.driven.wiring import excel_ports, sqlite_ports
from suivi.domain.model.wallet import WalletCatalog, WalletRef


def migrate(data_dir: str) -> int:
    source, target = excel_ports(data_dir), sqlite_ports(data_dir)
    catalog = source.registry.load()
    refs: list[WalletRef] = []
    for ref in catalog.wallets:
        location = target.locations.suggest_location(ref.name, [r.location for r in refs])
        target.ledgers.save(location, source.ledgers.load(ref.location))
        refs.append(WalletRef(ref.name, location))
    target.registry.save(WalletCatalog(tuple(refs), catalog.active))
    return len(refs)


if __name__ == "__main__":
    folder = os.path.dirname(os.path.abspath(__file__))
    print(f"{migrate(folder)} portefeuille(s) copié(s) vers {os.path.join(folder, 'suivi.db')}")
