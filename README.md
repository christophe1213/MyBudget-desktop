# Suivi des transactions — architecture hexagonale (ports & adaptateurs)

```
pip install -r requirements.txt      # openpyxl + customtkinter + sqlmodel
python main.py                       # écran de connexion, puis l'application (données Excel)
python main.py --no-auth             # sans écran de connexion (développement)
python main.py --classic             # interface tkinter classique (sans connexion)
python main.py --sqlite              # données financières dans SQLite (suivi.db) ; combinable
python -m unittest discover -s tests -t .
python migrate_excel_to_sqlite.py    # copie les portefeuilles Excel vers SQLite
pyinstaller --onefile --windowed --name SuiviTransactions main.py
```
Vos fichiers actuels (`transactions*.xlsx`, `portefeuilles.txt`) se lisent tels quels : copiez-les à côté de `main.py`.

## L'idée

Le **cœur** (métier + cas d'usage) ne connaît ni l'interface ni le stockage. Il parle au monde extérieur
uniquement par des **ports** (interfaces). Les **adaptateurs** branchent une technologie sur un port.

```
   ADAPTATEURS PILOTANTS                     CŒUR                         ADAPTATEURS PILOTÉS
   (ce qui commande l'appli)                                              (ce que l'appli commande)

 tkinter ┐                      ┌──────────── application ───────────┐      ┌ Excel (openpyxl)
 customtkinter ─────────► PORTS ENTRANTS ─► cas d'usage ─► PORTS SORTANTS ─► ┤ SQLite
 ligne de commande, API…        │               │                    │      └ SQLModel… (futur)
                                │               ▼                    │
                                │            DOMAINE (Python pur)    │      fichier texte, horloge,
                                └────────────────────────────────────┘      ouverture de fichiers
```

**Règle unique : les dépendances ne vont que vers l'intérieur** (adaptateurs → application → domaine).
`tests/test_architecture.py` la vérifie automatiquement : un import interdit fait échouer les tests.

## Où est quoi

| Dossier | Rôle | Peut importer |
|---|---|---|
| `suivi/domain/` | Entités (`Ledger`, `Transaction`, `Period`, `WalletCatalog`) et calculs (soldes, rapport, budget, analyse). **Python pur** | rien d'autre que la bibliothèque standard |
| `suivi/application/ports/inbound.py` | **Ports entrants** : ce que l'application offre (`ManageTransactions`, `PlanBudgets`…) | domaine |
| `suivi/application/ports/outbound.py` | **Ports sortants** : ce dont elle a besoin (`LedgerRepository`, `WalletRegistry`, `Clock`…) | domaine |
| `suivi/application/use_cases/`, `session.py` | Cas d'usage : orchestrent le domaine à travers les ports | domaine, application |
| `suivi/adapters/driven/` | Adaptateurs pilotés : `excel/`, `sqlite/`, registre texte, système | domaine, application, `openpyxl` |
| `suivi/adapters/driving/gui/` | Adaptateur pilotant : `contract/` (contrats des vues), `controllers/` (sans aucune bibliothèque graphique), `chart_painter.py` (graphique partagé), `ctk/` (**interface customtkinter**), `tk/` (interface tkinter classique) | domaine, application ; `customtkinter` dans `ctk/` seulement, `tkinter` dans `tk/` et `ctk/` |
| `suivi/bootstrap.py`, `main.py` | Racine de composition : seul endroit qui assemble les classes concrètes | tout |

Une transaction suit ce chemin : **vue** → **contrôleur** → **port entrant** → **cas d'usage** → **domaine**,
puis le cas d'usage enregistre via un **port sortant** → **adaptateur** (Excel/SQLite). Une modification est
faite sur une copie du livre, enregistrée, puis seulement adoptée : si Excel est ouvert, rien n'est modifié.

## Changer de technologie : que faut-il écrire ?

**Passer à SQLModel / SQLAlchemy / PostgreSQL** (stockage)
1. Créer `suivi/adapters/driven/sqlmodel/` avec des classes qui implémentent `LedgerRepository`,
   `LocationPolicy` et `WalletRegistry` (modèle : `adapters/driven/sqlite/storage.py`, 150 lignes).
2. Ajouter `sqlmodel_ports(...)` dans `adapters/driven/wiring.py` (un `DrivenPorts`).
3. Choisir ce lot dans `main.py`. Brancher le nouvel adaptateur sur `tests/test_storage_contract.py`
   (une sous-classe de 3 lignes) : s'il passe, il est interchangeable. **Rien d'autre ne change.**

**Interface customtkinter (déjà faite) et autres interfaces**
Les deux interfaces (`gui/ctk/` et `gui/tk/`) implémentent les mêmes contrats (`gui/contract/interfaces.py`) et
ne s'importent jamais l'une l'autre ; les contrôleurs servent aux deux. Pour une troisième (PySide, web...) :
une classe par vue + une `XxxUserInterface(UserInterface)`, puis le choix dans `main.py`.

**Charte de l'interface customtkinter** (tout est dans `gui/ctk/theme.py` : un seul fichier à modifier)
vert Excel `#217346` (navigation, boutons, en-têtes de tableaux, barres du graphique), fond blanc, surfaces
`#F6F9F7`, bleu (informations, moyenne), orange (avertissements, jours au-dessus du budget), rouge (suppression, erreurs).

**Une nouvelle règle métier** → `domain/` (+ un test dans `tests/test_domain.py`).
**Une nouvelle fonction** → un port entrant + son cas d'usage + un contrôleur/vue ; le domaine n'est touché
que si la règle est nouvelle.
**Une autre interface** (ligne de commande, API web) → un nouvel adaptateur pilotant qui appelle les mêmes ports entrants.

## Tableau de bord

Page d'accueil (onglet « Tableau de bord »), deux cartes :
- **Répartition des budgets restants** : camembert du solde de chaque budget (catégorie = dépôts − dépenses), légende
  « nom / montant · pourcentage ». Un solde négatif ne peut pas être une part de camembert : les catégories en déficit
  sont signalées sous le graphique.
- **Entrées et sorties selon les dates** : courbes des dépôts et des dépenses de chaque jour (zéros compris), valeurs sur
  les points, jour de plus forte sortie détaillé par catégorie. **Filtre entre deux dates** (Du / Au + Appliquer) et
  raccourcis « 7 j », « 30 j », « Tout ». Par défaut : les 14 derniers jours de données ; la période choisie est conservée
  quand les données changent.

Où : calcul dans `domain/services/dashboard.py` (Python pur) → port `ViewDashboard` → `DashboardController`.
Les dessins (`gui/dashboard_painter.py`) sont partagés par les deux interfaces (tkinter et customtkinter) :
seule la palette change.

## Authentification (SQLModel + SQLite)

Les **comptes** sont dans `comptes.db` (SQLModel) ; les **données financières** restent dans Excel : les deux
stockages sont indépendants (`AuthPorts` d'un côté, `DrivenPorts` de l'autre dans `bootstrap.py`).

| Couche | Contenu |
|---|---|
| Domaine | `Account` et règles d'identité : e-mail valide, mot de passe ≥ 8 caractères et pas trivial, clé de récupération tolérante à la saisie |
| Application | `AuthService` (port entrant `Authenticate`) : inscription, connexion, « Rester connecté·e » (30 jours), réinitialisation, déconnexion, verrouillage 5 min après 5 échecs |
| Ports sortants | `AccountRepository`, `PasswordHasher`, `RememberTokens`, `LocalSessionStore` |
| Adaptateurs | `sqlmodel_auth/store.py` (**seul fichier qui connaît SQLModel**), `security.py` (scrypt, bibliothèque standard), `local_session.py` (JSON) |
| Interface | `AuthController` + `ctk/auth_view.py` (écran en deux volets de la maquette) + carte utilisateur avec bouton de déconnexion |

Sécurité : mots de passe jamais conservés (empreinte scrypt avec sel aléatoire) ; jetons « Rester connecté » stockés
uniquement sous forme d'empreinte SHA-256 ; même message d'erreur pour un compte inconnu et un mauvais mot de passe ;
`session.json` lisible par le seul propriétaire (POSIX). « Mot de passe oublié » : clé de récupération remise une
seule fois à la création du compte (pas d'e-mail : l'application est locale), renouvelée à chaque réinitialisation.

**Changer l'ORM ou la base des comptes** (PostgreSQL, autre ORM) : réécrire `sqlmodel_auth/store.py` seulement.

## Les tests (106)

| Fichier | Ce qu'il prouve |
|---|---|
| `test_domain.py` | Les règles et les calculs, sans rien d'autre |
| `test_application_flows.py` | Les parcours complets (saisie, budget, analyse, portefeuilles, import, erreurs de stockage) avec des **adaptateurs en mémoire** (`fakes.py`) et des vues simulées : aucun fichier, aucune fenêtre |
| `test_storage_contract.py` | Le **même contrat** pour Excel et SQLite (+ fichiers anciens, fichier verrouillé, fichier invalide) |
| `test_architecture.py` | La règle de dépendance, le confinement de `tkinter`, `customtkinter`, `openpyxl`, `sqlite3`, le confinement de `sqlmodel` à `sqlmodel_auth/`, l'indépendance de `tk/` et `ctk/`, et des contrôleurs sans bibliothèque graphique |
| `test_tk_views_smoke.py` | Les **deux** interfaces (tkinter et customtkinter) respectent leurs contrats ; parcours complet pour chaque couple interface × stockage (bibliothèques simulées) |
| `test_chart_painter.py` | Le dessin du graphique (couleurs, jours au-dessus du budget, cas limites) |
| `test_dashboard.py` | Soldes par budget, flux par jour, filtre entre deux dates (valide et invalide), raccourcis, camembert et courbes |
| `test_migration.py` | Migration Excel → SQLite uniquement par les ports |
| `test_auth_service.py` | Règles de compte et cas d'usage d'authentification (verrouillage, jeton, expiration, réinitialisation) |
| `test_auth_adapters.py` | scrypt, SQLModel + SQLite réel, jeton jamais stocké en clair, session locale |
| `test_auth_controller.py` | L'écran d'authentification (vues simulées) : salutation, erreurs en ligne, reprise de session |
