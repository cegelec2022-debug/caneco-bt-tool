# Documentation technique — Valorisation des données CANECO BT

**Projet** : caneco-bt-tool
**Dépôt d'origine** : https://github.com/alysquart/caneco-bt-tool (branche stable : `main`, figé comme référence — tout repreneur travaille sur son propre fork, voir README section 1)
**Version documentée** : V1 (état au 12/07/2026)
**Cadre** : Challenge Innovation VEAO 2026 — Actemium Cegelec Tanger, VINCI Energies
**Équipe projet** : Aly Aly SANOH (Stagiaire Ingénieur), Mouhcine ZEKRAOUI (Responsable Études Électrique), M. Chakib ABBADI (Chef d'Entreprise)

Ce document décrit l'architecture, les services, le modèle de données, l'API et les procédures d'exploitation de l'outil, dans son état à la fin du stage PFE. Il complète le `README.md` (guide d'installation) et le `PRD.md` (vision produit et roadmap).

---

## 1. Vue d'ensemble

L'outil valorise les données issues de CANECO BT sur tout le cycle de vie du câble : études, achat, tirage chantier, DOE. Il s'organise en trois briques connectées autour d'une base PostgreSQL unique :

1. **Brique 1 — Vérification CANECO** : rapprochement automatique de la note CANECO avec le bordereau de prix et le CPS, vérification normative NF C 15-100, référentiel d'écarts E-001 à E-020.
2. **Brique 2 — Tableau de bord et saisie chantier** : pilotage multi-projets pour le RA, saisie mobile des longueurs réellement tirées par le Chef de Chantier, suivi du stock câbles.
3. **Brique 3 — Carnet de câbles, QR codes, DOE** : carnet de câbles selon la méthode CANECO, fiche publique par tableau accessible par scan QR, planches d'étiquettes A4. La génération du DOE complet est prévue en V2.

Cas pilotes : **DACHSER-L3** (principal, indice B : 699 lignes parsées, 23 colonnes) et **NSK-L3** (validation de la généricité).

---

## 2. Architecture générale

### 2.1 Couches

```
Frontend React (web + mobile responsive)
        | HTTPS / JSON (axios, TanStack Query)
API FastAPI (routers -> services -> repositories)
        |
PostgreSQL 16 (SQLAlchemy 2.x, migrations Alembic)
```

### 2.2 Stack technique

| Couche | Technologie | Version |
|---|---|---|
| Backend | Python + FastAPI | 3.11 / 0.115 |
| ORM / migrations | SQLAlchemy / Alembic | 2.0 / 1.14 |
| Base de données | PostgreSQL | 16 (image alpine) |
| Lecture Excel | openpyxl, xlrd, pandas | — |
| Lecture PDF | pdfplumber, pypdf | — |
| PDF générés | ReportLab | 4.2 |
| QR codes | qrcode + Pillow | 8.0 |
| Auth | python-jose (JWT) + passlib/bcrypt | — |
| Rate limiting | slowapi | 0.1.9 |
| Logs | loguru | 0.7 |
| Frontend | React 18 + TypeScript 5 + Vite 6 | — |
| UI | TailwindCSS 3 + shadcn/ui (Radix) | — |
| State serveur | TanStack Query 5 | — |
| Formulaires | react-hook-form + zod | — |
| Tests | pytest / Vitest | — |

### 2.3 Services Docker (docker-compose.yml)

| Service | Image / build | Port | Rôle |
|---|---|---|---|
| postgres | postgres:16-alpine | 5432 | Base de données, volume persistant `postgres_data` |
| backend | ./backend (python:3.11-slim) | 8000 | API FastAPI ; l'entrypoint attend la base, applique les migrations Alembic, exécute le seed puis lance uvicorn en mode reload |
| frontend | ./frontend | 5173 | Serveur de développement Vite ; les sources sont montées en volume (hot reload) |

Un second fichier, `docker-compose.preview.yml`, sert le build de production du frontend (`vite build && vite preview`) pour les démonstrations à distance via tunnel. Bascule :

```bash
# Développement
docker compose up -d
# Démonstration (build de production, pas de hot reload)
docker compose -f docker-compose.yml -f docker-compose.preview.yml up -d frontend
```

### 2.4 Variables d'environnement (backend)

| Variable | Rôle | Valeur en dev |
|---|---|---|
| DATABASE_URL | Connexion PostgreSQL | postgresql+psycopg://caneco_user:caneco_pass@postgres:5432/caneco_db |
| JWT_SECRET_KEY | Signature des tokens (min. 32 caractères ; l'application refuse de démarrer avec une valeur faible type "changeme") | valeur de dev dans docker-compose.yml |
| JWT_ALGORITHM | Algorithme JWT | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Durée de vie du token | 60 |
| CORS_ORIGINS | Origines autorisées (liste explicite, jamais *) | ["http://localhost:5173"] |
| PUBLIC_BASE_URL | URL publique encodée dans les QR codes | URL du tunnel ngrok |
| ANTHROPIC_API_KEY | Clé API Claude (optionnelle) | vide : mode 100 % déterministe |
| ENV | Environnement | development |

La configuration est centralisée dans `app/core/config.py` via pydantic-settings. Aucun `os.environ.get` direct dans la logique métier.

---

## 3. Backend

### 3.1 Organisation du code

```
backend/app/
├── api/
│   ├── routers/       13 routers REST (un par domaine)
│   ├── deps.py        Dépendances FastAPI (session DB, get_current_user)
│   └── access.py      Helper centralisé de contrôle d'accès projet
│                      (lecture vs écriture du dossier d'études, par rôle)
├── core/              config.py (pydantic-settings), security.py (JWT, bcrypt),
│                      logging.py (loguru), ratelimit.py (slowapi)
├── db/                base.py, session.py, seed.py (comptes démo + projet pilote)
├── models/            Modèles SQLAlchemy (14 tables)
├── schemas/           Schémas Pydantic (DTO API, extra="forbid" sur les entrées)
├── services/          Logique métier (détail en 3.4)
├── repositories/      Accès base de données
└── main.py            Application FastAPI, CORS, rate limiter, healthcheck
```

Convention imposée par le CLAUDE.md : noms français pour les entités métier (Projet, Tableau, Départ, Écart), anglais pour les couches techniques. Formatage Black (100 colonnes), lint Ruff, typage mypy strict sur les services métier, docstrings Google en français.

### 3.2 Authentification et rôles

- JWT signé HS256, durée 60 minutes, mots de passe hashés bcrypt.
- Rate limiting sur `POST /api/auth/login` et `/register` (slowapi).
- 4 rôles : `ADMIN`, `BE` (Responsable d'Études), `CHEF_CHANTIER`, `RA` (Responsable d'Affaires).
- L'identité pour toute écriture vient du token, jamais du body.
- `app/api/access.py` factorise le contrôle d'accès : le Chef de Chantier a accès en lecture aux projets actifs et en écriture aux saisies chantier et livraisons stock, mais aucun accès en écriture au dossier d'études (uploads CANECO / bordereau / CPS, vérifications).

### 3.3 Référence API

Toutes les routes sont préfixées `/api`. Sauf mention contraire, elles exigent un token JWT (`Authorization: Bearer`). Documentation interactive : `http://localhost:8000/api/docs`.

**Authentification (`/api/auth`)**

| Méthode | Route | Rôle |
|---|---|---|
| POST | /api/auth/login | Connexion, retourne le token JWT |
| POST | /api/auth/register | Création de compte (rate-limitée) |
| GET | /api/auth/me | Profil de l'utilisateur courant |

**Projets (`/api/projects`)**

| Méthode | Route | Rôle |
|---|---|---|
| GET / POST | /api/projects/ | Liste / création |
| GET / PATCH / DELETE | /api/projects/{id} | Détail / mise à jour (dont paramètres avancement) / suppression |
| GET | /api/projects/{id}/metrics | Métriques du projet (avancement, écarts, métrés) |

**Imports études (par projet)**

| Méthode | Route | Rôle |
|---|---|---|
| POST | .../caneco/upload | Upload d'un export CANECO (.xls/.xlsx) |
| GET | .../caneco, .../caneco/{export_id} | Liste / détail des lignes parsées |
| PATCH | .../caneco/{export_id}/indice | Changer l'indice actif (A, B, C...) |
| GET | .../caneco/{export_id}/export-excel | Réexport Excel |
| DELETE | .../caneco/{export_id} | Suppression |
| POST | .../bordereau/preview-sheets | Lister les feuilles du classeur avant import |
| POST | .../bordereau/upload | Upload du bordereau de prix |
| GET / PATCH / DELETE | .../bordereau[...] | Liste, détail, indice, suppression |
| POST / GET / DELETE | .../cps-imports[...] | Upload et gestion des CPS PDF |

**Vérification**

| Méthode | Route | Rôle |
|---|---|---|
| POST | .../verification-runs | Lance une vérification complète |
| GET | .../verification-runs[/{run_id}] | Historique / détail d'un run |
| GET | .../verification-runs/{run_id}/gaps | Écarts du run (filtrables) |
| PATCH | .../verification-runs/{run_id}/gaps/{gap_id} | Lever / justifier un écart |
| DELETE | .../verification-runs/{run_id} | Suppression d'un run |

**Carnet, tableaux, chantier, stock**

| Méthode | Route | Rôle |
|---|---|---|
| GET | .../cable-book | Carnet de câbles (sommaire par type/section/âme) |
| GET | .../cable-book/by-tableau | Carnet groupé par tableau |
| GET | .../cable-book/export.xlsx | Export Excel du carnet |
| POST | .../tableaux/generate | Dérive les tableaux depuis l'export CANECO actif (idempotent, conserve les qr_token existants) |
| GET | .../tableaux | Liste des tableaux et de leurs départs |
| GET | .../tableaux/{tableau_id}/qr.png | QR code unitaire |
| GET | .../tableaux/labels.pdf | Planche A4 de 8 étiquettes à découper |
| GET | .../tableaux/{tableau_id}/fiche.pdf | Fiche tableau PDF |
| PUT / DELETE | .../field-entries/{caneco_line_id} | Saisie chantier : longueur réelle + commentaire (1 saisie par ligne CANECO) |
| GET | .../field-entries | Toutes les saisies du projet |
| GET / PUT / DELETE | .../cable-stock[...] | Stock câbles : quantités achetées / livrées, seuils d'alerte |

**Tableau de bord et route publique**

| Méthode | Route | Rôle |
|---|---|---|
| GET | /api/dashboard/summary | Synthèse multi-projets (KPI RA) |
| GET | /api/t/{token} | Fiche tableau publique (SEULE route non authentifiée, lecture seule, rate-limitée, données minimales) |
| GET | /api/t/{token}/fiche.pdf | Fiche publique en PDF |
| GET | /api/health | Healthcheck |

### 3.4 Services métier (`app/services/`)

**caneco/** — Parser des exports CANECO BT (.xls via xlrd, .xlsx via openpyxl). 23 colonnes typées par ligne (Repère, Désignation, Style, Consommation, IB, Longueur, Type de câble, Câble, Neutre, PE, Âme, Calibre, IrTh, IrMg, Icu, etc.). Un tableau électrique est une ligne dont le style contient tableau / armoire / coffret (règle générique tous projets).

**bordereau/** — Parser du bordereau de prix Excel. Pré-visualisation des feuilles du classeur, sélection de la feuille utile (DACHSER : « BDP_ELECTRICITE CFO »), extraction des lignes et sections.

**cps/** — Parser des CPS PDF (pdfplumber) : extraction des exigences chiffrables (sections minimales, types de câble imposés, DDR, IP, schéma de mise à la terre).

**verification/** — Moteur de vérification déterministe, cœur de la Brique 1 :

| Composant | Rôle |
|---|---|
| engine.py | Orchestre l'enchaînement des vérifications d'un run |
| line_matcher.py | Rapprochement ligne CANECO / ligne bordereau (similarité type Jaro-Winkler + règles métier, score de confiance) |
| cable_comparator.py | Comparaison sections, types, matières de câble |
| norm_checker.py | Vérification NF C 15-100 ; règles externalisées dans `nfc15100_rules.json` (modifiables sans toucher au code) |
| protection_checker.py | Cohérence des protections : IB > In (E-004), réglage IrTh, pouvoir de coupure Icu (E-011) |
| cps_checker.py | Confrontation aux exigences extraites du CPS |
| suggestion_engine.py | Bonnes pratiques non bloquantes ; règles dans `suggestions_rules.json` |
| gap_emitter.py | Accumule les écarts au format normalisé avant persistance |

Sévérités : `BLOQUANT`, `A_CORRIGER`, `A_SIGNALER`, `INFO`. Le référentiel d'écarts, initialement E-001 à E-010 (PRD), a été étendu à **E-001 à E-020** (Icu insuffisant, IrTh insuffisant, sous-tableaux non appariés, règles CPS sans correspondance ou non respectées, champs manquants, etc.).

Résultat de référence (DACHSER indice B, run du 05/06/2026) : 2 415 écarts détectés dont 2 bloquants E-004 (protection sous-calibrée IB > In sur les départs TAM), confirmés manuellement.

**cable_book/** — Carnet de câbles selon la méthode CANECO BT v5.x : chaque ligne est décomposée en conducteurs unipolaires (câbles `nXm(1xS)`, conducteurs Neutre / PE / PEN). Le `n` extérieur des câbles parallèles n'est pas re-multiplié (correction d'un double comptage). Colonne Âme (Cuivre / Alu). Validation DACHSER indice C : 41 616 m calculés contre 41 746 m dans le PDF officiel CANECO, soit un écart de -0,31 %.

**tableau/** et **qr/** — Dérivation des tableaux depuis l'export CANECO actif (regroupement par amont), idempotente : la régénération conserve les `qr_token` existants, donc les étiquettes déjà collées restent valides. Token généré par `secrets.token_urlsafe(32)`, sans lien avec les identifiants internes. QR codes avec correction d'erreur H et logo VINCI centré. Planches A4 de 8 étiquettes avec repères de découpe (ReportLab). Fiche tableau PDF avec en-tête rouge VINCI.

**field_entry (router + service)** — Saisie chantier : une saisie par ligne CANECO (longueur réelle, commentaire). Règle métier : commentaire **obligatoire** si la longueur vaut 0 (circuit non tiré) ou si l'écart absolu au prévu dépasse 50 %. Validée côté backend (422) et côté front.

**cable_stock/** — Stock câbles par référence (type, section, âme) : `quantite_achetee` (RA), `quantite_livree` (Chef), `quantite_utilisee` calculée en direct depuis les saisies chantier, ventilée selon la même décomposition que le carnet (une saisie de 100 m sur `3X(1x150)` alimente la référence 1x150 Alu à hauteur de 300 m). Seuil d'alerte configurable par référence. Le stock liste toutes les références du carnet CANECO, pas seulement celles déjà mouvementées.

**project_metrics.py** et **dashboard (router)** — Métriques par projet (avancement, écarts ouverts, métrés prévus / tirés) et synthèse multi-projets pour le RA. Formule d'avancement paramétrable par projet (onglet Paramètres) : `avancement = poids_tirage x % circuits saisis + poids_validation x % validation`.

**llm/adapter.py** — Adapter optionnel vers l'API Claude (Anthropic) pour les documents non structurés et la reformulation d'écarts. Le moteur déterministe reste la source de vérité : le LLM ne peut jamais invalider un écart détecté. Sans clé API, l'outil fonctionne intégralement en mode déterministe. Non branché en production à ce jour.

**doe/** — Répertoire créé, service **non implémenté** (priorité 1 de la V2). Les fiches tableau PDF unitaires existent déjà ; il reste l'assemblage du DOE complet (page de garde, sommaire, fiches, prévu/réalisé, photos, versionnement).

### 3.5 Modèle de données

14 tables (PostgreSQL, migrations Alembic 001 à 013) :

| Table | Contenu |
|---|---|
| users | Comptes et rôles (ADMIN, BE, CHEF_CHANTIER, RA) |
| projects | Projets (code, client, agence, statut, paramètres d'avancement) |
| caneco_exports / caneco_lines | Imports CANECO et leurs lignes (23 colonnes typées, indice actif) |
| bordereau_imports / bordereau_sections / bordereau_lines | Bordereau de prix (feuille choisie, sections, lignes) |
| cps_imports | CPS PDF importés et règles extraites |
| verification_runs / gaps | Runs de vérification et écarts (code E-xxx, sévérité, lignes source, action suggérée, statut de levée) |
| tableaux / departures | Tableaux électriques dérivés et leurs départs (qr_token public) |
| field_entries | Saisies chantier (longueur réelle, commentaire, 1 par ligne CANECO) |
| cable_stock_items | Références de stock câble (acheté / livré / seuil) |

### 3.6 Seed de démonstration

`app/db/seed.py`, exécuté automatiquement au démarrage du backend (entrypoint). Crée s'ils n'existent pas :

- 4 comptes : admin@actemium.fr, be@actemium.fr, chef@actemium.fr, ra@actemium.fr (mot de passe commun `Demo2026!`)
- Le projet pilote `DACHSER-L3` (client DACHSER, agence Actemium Cegelec Tanger)

Les fichiers de référence à uploader sont dans `data/seed/dachser/` (règle absolue : ne jamais les modifier ni les supprimer).

---

## 4. Frontend

### 4.1 Pages (`src/pages/`)

| Page | Rôle |
|---|---|
| LoginPage | Connexion (avec boutons de connexion démo en 1 clic) |
| ProjectsPage | Liste des projets |
| ProjectPage | Page projet à onglets : Vue, Études, Bordereau, CPS, Vérifs, Carnet, Tableaux, Saisie chantier, Stock, DOE, Paramètres |
| DashboardPage | Tableau de bord multi-projets RA : KPI globaux, filtres / tris, drill-down par projet (alertes stock, écarts bloquants) |
| FicheTableauPublic | Fiche publique `/t/:token`, mobile-first, atteinte par scan QR |

### 4.2 Comportements notables

- **Permissions d'affichage** : le Chef de Chantier ne voit pas les onglets Bordereau / CPS / Vérifications ; son onglet par défaut est Saisie chantier.
- **Mode présentation** sur l'écran Vérifs : toggle n'affichant que les écarts Bloquants et À corriger (utilisé en démonstration jury).
- **Responsive mobile** : sidebar en drawer (menu hamburger), barre d'onglets à défilement horizontal, en-têtes de tableaux épinglés.
- **Saisie chantier** : champ longueur réelle + commentaire repliable, indicateur d'écart coloré (vert <= 5 %, jaune 5-10 %, rouge > 10 %), bouton bloqué tant que le commentaire obligatoire n'est pas rempli.
- **Charte** : rouge VINCI `#C8102E` en accent (onglet actif, alertes), bleu nuit `#001E50` en structure, composants shadcn/ui, police Inter. Pas d'emoji.

### 4.3 Couche d'accès API

`src/api/` : un module par domaine (axios, baseURL relative, proxy Vite `/api` vers le backend). État serveur géré par TanStack Query (staleTime, invalidations après mutation). Types TypeScript partagés dans `src/types/`.

---

## 5. Sécurité

Règles appliquées (détail : `CLAUDE.md` et `docs/SECURITY_AUDIT_PROMPT.md`) :

- Aucun secret en dur ; configuration par pydantic-settings ; `.env` jamais commité (vérifié par `.gitignore`), seuls les `.env.example` le sont.
- Toutes les routes protégées passent par `Depends(get_current_user)` ; contrôle d'accès à la ressource avant tout traitement (`app/api/access.py`).
- Schémas Pydantic d'entrée en `extra="forbid"` ; ils n'acceptent ni id, ni user_id, ni role.
- Uploads : vérification du type MIME côté serveur, taille maximale (50 Mo Excel, 100 Mo PDF), stockage hors dossiers servis statiquement, parsing sans exécution de macros.
- Route publique unique `GET /api/t/{token}` : lecture seule, token imprévisible (secrets.token_urlsafe(32)), réponse minimale (ni code projet, ni client), rate-limitée.
- CORS : liste d'origines explicite, en-têtes limités à Authorization et Content-Type.
- Logs : métadonnées uniquement, jamais de contenu de fichier ni de token ; en production le handler global retourne « Internal server error » sans détail.
- Avant chaque tag de version : audit complet selon `docs/SECURITY_AUDIT_PROMPT.md` ; aucune conclusion CRITIQUE ne doit rester ouverte.

---

## 6. Tests

- **Backend** : pytest, 238+ tests verts (auth, projets, saisie chantier, stock, dashboard, route publique, accès tableaux, services de parsing et de vérification). `backend/tests/conftest.py` fournit une base et des utilisateurs de test isolés.
- **Frontend** : Vitest + Testing Library (`src/__tests__/`).

```bash
docker compose exec backend pytest            # backend, dans le conteneur
cd backend && pytest --cov=app                # backend local avec couverture
cd frontend && npm test                       # frontend
```

Un principe du projet : le moteur de vérification, les parsers et le futur générateur de DOE visent une couverture > 80 %.

---

## 7. Exploitation et démonstration

### 7.1 Cycle de vie local

```bash
docker compose up -d          # démarrer (migrations + seed automatiques)
docker compose logs -f        # surveiller
docker compose down           # arrêter
docker compose down -v        # arrêter et remettre la base à zéro
```

### 7.2 Démonstration à distance (tunnel ngrok)

Pour que les QR codes scannés par téléphone fonctionnent et pour montrer l'outil hors du poste de développement :

- `PUBLIC_BASE_URL` (docker-compose.yml) doit contenir l'URL publique ; elle est encodée dans les QR codes générés. Après changement, régénérer les tableaux.
- Le tunnel historique du projet utilise le SDK Node `@ngrok/ngrok` en process Windows détaché, avec URL stable liée au compte ngrok. Contrainte du plan gratuit : une seule instance de tunnel à la fois ; page interstitielle « Visit Site » au premier accès.
- Pour un pitch fluide, servir le build de production : `docker compose -f docker-compose.yml -f docker-compose.preview.yml up -d frontend`.

### 7.3 Comptes de démonstration

Voir README section 3.4 (admin / be / chef / ra @actemium.fr, mot de passe `Demo2026!`). À remplacer par de vrais comptes avant tout déploiement réel.

---

## 8. État d'avancement et reste à faire

**Livré en V1** : les trois briques fonctionnelles décrites ci-dessus, validées en démonstration sur DACHSER-L3 et NSK-L3.

**Reporté (V2, par priorité)** :

1. Génération du DOE complet PDF + Excel, versionnée (`services/doe` vide à ce jour).
2. Photos en justification des écarts chantier (US-CC-03).
3. Mode hors-ligne PWA avec synchronisation différée (US-CC-04 / US-CC-05).
4. Activation de la couche LLM en production (adapter présent, non branché).
5. Transfert de matériel inter-projets, alertes e-mail, comparaison d'indices A/B.

La roadmap complète (V2, V3, V4) est tenue à jour dans `PRD.md`, section 9.

---

## 9. Conventions de contribution

- Branches : `main` stable ; travail sur `feat/<description>`, `fix/<description>`, `docs/<description>`.
- Commits : Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`). Un commit = une intention.
- Python : Black (100 colonnes), Ruff, isort, mypy strict sur les services métier, docstrings Google en français.
- TypeScript : strict, Prettier, ESLint, pas de `any` non justifié, imports absolus `@/`.
- Mettre à jour `CHANGELOG.md` à chaque fonctionnalité livrée.
- Ne jamais modifier `data/seed/` ; ne jamais committer de `.env` ; pas d'emoji.
- Avant chaque tag : audit de sécurité complet (`docs/SECURITY_AUDIT_PROMPT.md`).

Le fichier `CLAUDE.md` à la racine rend toutes ces règles opposables à Claude Code automatiquement à chaque session.
