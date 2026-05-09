# Prompt initial Claude Code

> Ce fichier contient **le prompt à coller dans Claude Code** pour démarrer le projet.
> Tu peux le copier-coller en deux temps : d'abord le bloc « Setup », puis le bloc « V1 ».
> Tu n'as **pas** besoin de tout lire : Claude Code fera le travail.

---

## Bloc 1 — Setup initial (à envoyer en premier)

Copie-colle exactement ce bloc dans Claude Code, depuis la ligne `===== DÉBUT BLOC 1 =====` jusqu'à `===== FIN BLOC 1 =====` (sans inclure ces deux lignes).

```
===== DÉBUT BLOC 1 =====

Tu es l'assistant développeur principal du projet "Valorisation des données CANECO BT" pour le Challenge Innovation VEAO 2026 (VINCI Energies / Actemium Cegelec).

# Contexte projet

Avant de commencer, lis intégralement les documents suivants présents dans le dossier `docs/` du projet :

1. `docs/PRD.md` — vision produit, personas, périmètre fonctionnel V1
2. `docs/cahier_des_charges.md` — spécifications fonctionnelles et techniques détaillées
3. `docs/cartes_empathie.md` — synthèse des trois personas (extraction du DOCX livré)
4. `docs/brief_pitch.md` — narratif de soutenance (extraction du DOCX livré)
5. `CLAUDE.md` — instructions persistantes (style, conventions, garde-fous)

Ces documents sont la source de vérité du projet. Toute décision technique doit y être conforme.

# Données de référence

Le dossier `data/seed/dachser/` contient :
- `DATA_DACHSER_INDICE_B.XLS` (export CANECO BT, 700 lignes, 23 colonnes)
- `Pièce_03_Bordereau_des_Prix_DACHSER_LOT3.xlsx` (bordereau, feuille « BDP_ELECTRICITE CFO »)
- `Pièce_021_Clauses_techniques_DACHSER_LOT3.pdf` (CPS)
- `Pièce_02-2_Descriptif_des_ouvrages_DACHSER_LOT3.pdf` (descriptif)

Le projet doit produire des résultats corrects sur ces fichiers.

# Mission de cette première session

Mettre en place le squelette technique complet du projet, prêt à recevoir le développement des fonctionnalités V1.

## 1. Initialisation du dépôt

Crée un dépôt git local à la racine du projet, avec :
- `.gitignore` complet pour Python, Node, IDE, OS, Docker
- `.editorconfig` standard
- Un commit initial nommé `chore: initialisation du dépôt`

## 2. Structure de dossiers

Crée la structure suivante (vide ou avec fichiers placeholders selon les besoins) :

```
.
├── backend/
│   ├── app/
│   │   ├── api/routers/
│   │   ├── api/deps.py
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/caneco/
│   │   ├── services/bordereau/
│   │   ├── services/cps/
│   │   ├── services/verification/
│   │   ├── services/doe/
│   │   ├── services/qr/
│   │   ├── services/llm/
│   │   ├── repositories/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/ui/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── api/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   └── .env.example
│
├── docs/
├── data/seed/dachser/
├── docker-compose.yml
├── README.md
├── CLAUDE.md
└── .env.example
```

## 3. Configuration backend Python

Crée `backend/pyproject.toml` avec les dépendances suivantes :

- fastapi, uvicorn[standard], pydantic, pydantic-settings
- sqlalchemy, alembic, psycopg[binary]
- python-jose[cryptography], passlib[bcrypt], python-multipart
- openpyxl, xlrd==1.2.0, pandas
- pdfplumber, pypdf, reportlab
- qrcode[pil], pillow
- python-Levenshtein (pour le rapprochement de chaînes)
- loguru
- httpx (pour le client LLM)
- anthropic (en dépendance optionnelle)

Dépendances de dev : pytest, pytest-asyncio, pytest-cov, black, ruff, mypy, isort.

Configure ruff (ligne max 100, règles: E, F, W, I, B, UP), black (ligne max 100), isort (profile black), mypy (strict sur app/services et app/core).

Crée `backend/app/main.py` minimal qui démarre FastAPI avec :
- CORS configuré pour `http://localhost:5173` (front Vite)
- Healthcheck `GET /api/health` qui retourne `{"status": "ok"}`
- Documentation Swagger sur `/api/docs`

Crée `backend/app/core/config.py` avec une classe `Settings` (pydantic-settings) qui lit `.env`. Variables :
- `DATABASE_URL`
- `JWT_SECRET_KEY` (générée par défaut si absente, avec warning)
- `JWT_ALGORITHM` = "HS256"
- `ACCESS_TOKEN_EXPIRE_MINUTES` = 60
- `ANTHROPIC_API_KEY` (optionnelle, peut être None)
- `CORS_ORIGINS` (liste, défaut `["http://localhost:5173"]`)
- `ENV` = "development"

Crée `backend/.env.example` qui documente toutes les variables.

## 4. Configuration frontend React

Initialise un projet Vite + React + TypeScript dans `frontend/`.

Installe :
- TailwindCSS, postcss, autoprefixer
- shadcn-ui CLI (et configure avec un thème custom basé sur `--vinci-red: #C8102E` et `--vinci-blue: #001E50`)
- react-router-dom, @tanstack/react-query, axios
- react-hook-form, zod, @hookform/resolvers
- lucide-react (icônes)
- html5-qrcode (scan QR côté client)
- date-fns

Configure :
- `tsconfig.json` avec strict, alias `@/* → src/*`
- `tailwind.config.ts` avec les couleurs VINCI dans `theme.extend.colors`
- `vite.config.ts` avec proxy vers `http://localhost:8000` pour `/api`

Génère via shadcn-ui les composants suivants : button, input, label, card, dialog, sheet, tabs, table, toast, badge, separator, select, checkbox, dropdown-menu, alert, alert-dialog, form.

Crée `frontend/src/lib/colors.ts` qui exporte les constantes de couleur VINCI (toutes les couleurs définies dans le PRD, section 7.1).

## 5. Docker compose

Crée `docker-compose.yml` à la racine avec trois services :
- `postgres` (postgres:16-alpine, port 5432, volume nommé)
- `backend` (build depuis backend/Dockerfile, dépend de postgres, port 8000, hot-reload)
- `frontend` (build depuis frontend/, port 5173, hot-reload)

Crée les Dockerfile correspondants. Utilise des images de base légères et builds multi-stage pour la production.

## 6. Base de données

Initialise Alembic dans `backend/alembic/`.

Crée les modèles SQLAlchemy de base dans `backend/app/models/` selon le modèle de données du PRD section 8 (13 entités). Pour cette première session, crée au minimum :
- `User`
- `Project`
- `CanecoExport`
- `CanecoLine`
- `Bordereau`
- `BordereauLine`
- `Tableau`
- `Departure`

Génère et applique la première migration Alembic.

## 7. README et démarrage

Crée un `README.md` à la racine qui explique :
- Le projet (en 5 lignes)
- Les prérequis (Docker, Node 20+, Python 3.11+)
- La commande pour démarrer en dev : `docker compose up -d`
- L'accès au frontend (http://localhost:5173) et à l'API (http://localhost:8000/api/docs)
- Comment lancer les tests (back et front)

## 8. Validation finale

À la fin de cette session :
1. Lance `docker compose up -d` et vérifie que les trois services démarrent.
2. Teste que `curl http://localhost:8000/api/health` retourne `{"status": "ok"}`.
3. Teste que `http://localhost:5173` affiche la page d'accueil React (même vide).
4. Crée un commit `chore: squelette technique du projet`.

# Règles de comportement

- Ne jamais inventer un chiffre, une métrique, un fait métier qui ne soit pas dans les sources du projet.
- Pas d'emoji dans le code, les commentaires ou les UI utilisateur.
- Pour chaque dépendance ajoutée, justifie en une ligne dans un commentaire ou un commit.
- Si un point du PRD est ambigu, demande avant d'inventer.
- Si une commande shell échoue, arrête-toi, explique l'erreur, propose une solution.

Commence par confirmer que tu as bien lu les documents du dossier `docs/` et que la structure du projet est claire pour toi. Puis exécute les étapes 1 à 8 dans l'ordre, en commitant à chaque étape majeure.

===== FIN BLOC 1 =====
```

---

## Bloc 2 — Développement V1 (à envoyer après le bloc 1)

Une fois que Claude Code a terminé le setup, copie-colle ce second bloc.

```
===== DÉBUT BLOC 2 =====

Maintenant que le squelette est en place, on développe la V1 fonctionnelle.

# Plan de bataille

On découpe le développement en 6 modules. À la fin de chaque module, tu commit, tu lances les tests, et tu fais une démo dans le terminal pour valider.

## Module 1 — Authentification et gestion des projets

Implémente :
- Endpoint `POST /api/auth/login` (email + password → JWT)
- Endpoint `POST /api/auth/register` (création d'un compte, à désactiver en production)
- Endpoint `GET /api/auth/me` (récupère l'utilisateur courant)
- Modèle User avec rôles : `BE`, `chef_chantier`, `RA`, `admin`
- Routes CRUD `/api/projects` (GET, POST, PATCH, DELETE), filtrage par rôle utilisateur
- Page de connexion frontend (formulaire email/password, validation zod, react-hook-form)
- Page liste des projets (carte par projet, bouton « Nouveau projet »)
- Page projet (onglets : Vue d'ensemble, Études, Tableaux, DOE)
- Layout principal avec sidebar de navigation (logo VINCI Energies, menu selon rôle)

Ajoute les tests pytest pour les endpoints d'auth et de projet, et un test E2E simple côté front avec Vitest.

Seed : crée un utilisateur de test `admin@actemium.fr` / `Demo2026!` avec rôle admin, et un projet de démo "DACHSER — Lot 3 Électricité".

## Module 2 — Parser CANECO

Implémente le service `app/services/caneco/parser.py` qui :
- Accepte un chemin de fichier `.xls` ou `.xlsx`
- Extrait toutes les lignes en respectant les 23 colonnes (Repère, Désignation, Style, Nb récepteurs, Consommation, IB, Longueur, Type de câble, Câble, Neutre, PE ou PEN, Ame, Calibre, Bloc de coupure, Bloc déclencheur, Bloc différentiel, IrTh / IN, IrMg / IN, Icu, et toute autre)
- Normalise les valeurs (nombres parsés en float, sections normalisées au format "5G6", types de câble en majuscules sans espaces)
- Retourne une liste d'objets `CanecoLineDto` (Pydantic)

Endpoint `POST /api/projects/{id}/caneco-imports` qui upload un fichier Excel, le parse, et stocke les lignes en base.

Endpoint `GET /api/projects/{id}/caneco-imports` pour lister les indices uploadés.

Frontend : composant d'upload (drag & drop) sur l'onglet Études, table des lignes parsées (avec pagination, recherche).

Tests :
- Le parser doit traiter le fichier `data/seed/dachser/DATA_DACHSER_INDICE_B.XLS` sans erreur.
- 700 lignes parsées, 23 colonnes par ligne.
- Test unitaire des fonctions de normalisation.

## Module 3 — Parser bordereau et CPS, moteur de vérification

### 3.1 Parser bordereau

Service `app/services/bordereau/parser.py` :
- Accepte un fichier `.xlsx`
- Détecte automatiquement la feuille pertinente (recherche par mot-clé : « BDP », « ELECTRICITE », « CFO »)
- Extrait les colonnes : N° de prix, désignation, unité, quantité, prix unitaire, montant
- Retourne une liste d'objets `BordereauLineDto`

### 3.2 Parser CPS

Service `app/services/cps/parser.py` :
- Accepte un PDF
- Extrait les exigences chiffrables (sections minimales mentionnées, types de câble imposés, IP minimum)
- Mode V1 : règles déterministes par mot-clé (regex)
- Mode V2 (préparé mais désactivé) : fallback LLM via `app/services/llm/adapter.py`

### 3.3 Moteur de vérification

Service `app/services/verification/engine.py` qui orchestre :
1. `LineMatcher` : rapproche chaque ligne CANECO avec une ligne bordereau (Levenshtein sur le repère + matching sur type de câble + section), avec score de confiance
2. `NormChecker` : applique les règles NF C 15-100 (table de règles dans `app/services/verification/nfc15100_rules.json`)
3. `GapEmitter` : émet les écarts au format E-001 à E-010

Endpoint `POST /api/projects/{id}/verification-runs` qui lance une vérification asynchrone.
Endpoint `GET /api/verification-runs/{id}` pour le statut.
Endpoint `GET /api/verification-runs/{id}/gaps` pour la liste des écarts (filtrable, paginée).
Endpoint `PATCH /api/gaps/{id}` pour lever un écart (statut, commentaire).

Frontend :
- Bouton « Lancer la vérification » sur l'onglet Études
- Page rapport d'écarts : compteurs par criticité, table filtrable, panneau latéral de détail
- Boutons d'export (PDF, Excel)

Tests : sur le projet DACHSER, le moteur doit produire un rapport en moins de 10 secondes, avec un nombre d'écarts cohérent (validé par snapshot test).

## Module 4 — QR codes et fiches tableau

### 4.1 Génération QR

Service `app/services/qr/generator.py` :
- Pour chaque tableau d'un projet, génère un QR code dont le payload est une URL `https://<domain>/t/<token>` où `token` est un identifiant aléatoire long (32 caractères)
- Le QR contient le logo Cegelec en surimpression au centre (image fournie)
- Le token est stocké en base et permet d'accéder à la fiche tableau sans authentification

### 4.2 Page fiche tableau

Route publique `/t/<token>` (frontend), qui :
- Affiche un en-tête rouge VINCI / Cegelec avec le repère du tableau
- Affiche un tableau avec les colonnes CANECO (Repère, Désignation, Style, Nb récepteurs, Consommation, IB, Longueur, Type de câble, Câble, Neutre, PE ou PEN, Calibre, Bloc de coupure, Bloc déclencheur, Bloc différentiel, IrTh / IN, IrMg / IN)
- Bouton « Voir le PDF » qui télécharge la fiche en PDF
- Responsive optimisé mobile (utilisable sur smartphone)

Reproduit le design des images de référence dans `docs/assets/fiche_tableau_reference.jpg`.

### 4.3 Génération de planches A4 d'étiquettes

Endpoint `GET /api/projects/{id}/qr-sheet?cols=2&rows=4` qui retourne un PDF A4 contenant plusieurs étiquettes QR (8 par défaut, configurable).

Chaque étiquette comprend :
- QR code (avec logo Cegelec au centre, encadré arrondi gris-bleu)
- Bandeau gris en dessous avec le repère du tableau (TGBT, TES1, etc.)
- Marges de découpe

Frontend : bouton « Imprimer les étiquettes QR » sur l'onglet Tableaux, qui télécharge le PDF.

## Module 5 — Application chantier (mobile, PWA)

### 5.1 PWA

Configure `vite-plugin-pwa` pour transformer le frontend en PWA installable. Manifest avec icônes 192x192 et 512x512 (générées à partir du logo VINCI). Service worker pour cache offline-first des assets statiques.

### 5.2 Pages mobiles

- Route `/m/projects` : liste des projets accessibles à l'utilisateur, version mobile compacte
- Route `/m/scan` : page de scan QR (utilise html5-qrcode)
- Route `/m/tableaux/<id>` : fiche tableau en mode édition (départs avec champs longueur réalisée)
- Route `/m/tableaux/<id>/departures/<departure_id>` : saisie d'un départ (longueur, photo, commentaire)

### 5.3 Saisie hors-ligne

Pour la V1 simplifiée : on ne fait pas le offline-first complet. On affiche un indicateur de connexion et on bloque la saisie en mode hors-ligne, avec un message « Vous êtes hors ligne. La saisie sera disponible au retour de la connexion. » (le offline-first complet est V2 — voir PRD).

### 5.4 Endpoints

- `GET /api/tableaux/<token>` : fiche tableau publique (sans auth)
- `POST /api/departures/<id>/field-entries` : saisie d'une longueur (avec auth)
- `POST /api/field-entries/<id>/photos` : upload d'une photo (multipart/form-data)

## Module 6 — Tableau de bord RA et génération DOE

### 6.1 Tableau de bord

Endpoint `GET /api/dashboard` qui retourne pour le RA :
- Nombre de projets actifs
- Nombre d'écarts ouverts (toutes criticités)
- Nombre d'alertes critiques
- Liste des projets avec : code, client, avancement, écarts ouverts, marge prévisionnelle
- Top 5 des projets en dépassement

Frontend : page `/dashboard` avec cartes de KPI, table des projets (sortable, filtrable), graphique simple (recharts) du temps de complétude par projet.

### 6.2 Génération DOE

Service `app/services/doe/generator.py` qui produit, pour un projet :
- Un PDF complet avec : page de garde, table des matières, fiches de chaque tableau, longueurs prévues vs réalisées, photos terrain, écarts levés / non levés
- Un Excel parallèle avec les données brutes

Endpoint `POST /api/projects/{id}/doe` qui génère le DOE et retourne un job_id, puis `GET /api/jobs/{id}` pour récupérer l'URL de téléchargement.

Frontend : onglet DOE avec bouton « Générer le DOE » et historique des versions.

## Validation finale V1

À la fin du Module 6 :
1. Lance la suite de tests complète (`pytest` côté back, `pnpm test` côté front).
2. Démo manuelle : connexion → liste projets → page projet DACHSER → upload CANECO → upload bordereau → vérification → rapport d'écarts → génération DOE.
3. **Avant de créer le tag `v0.1.0`, lance l'audit de sécurité** : ouvre `SECURITY_AUDIT_PROMPT.md`, copie le prompt complet (entre les balises `===== DÉBUT PROMPT =====` et `===== FIN PROMPT =====`) et envoie-le-moi pour le faire dérouler. Aucune conclusion CRITIQUE ne doit rester ouverte. Les conclusions HAUTES sont corrigées immédiatement, les MOYENNES et BASSES peuvent être planifiées en V1.1.
4. Une fois l'audit passé, crée le tag git `v0.1.0` sur la branche main.
5. Mets à jour le `CHANGELOG.md` avec la liste des fonctionnalités V1 et la mention de l'audit de sécurité passé.

# Règles importantes

- Travaille **module par module**. Termine complètement un module (back + front + tests) avant de passer au suivant.
- À chaque fin de module, **commit, push, puis attends ma validation** avant de passer au suivant.
- Si tu rencontres un blocage, **arrête-toi et explique** plutôt que de t'écarter du PRD.
- **Pas d'emoji nulle part**. Le projet est destiné à un environnement professionnel VINCI Energies.

Commence par le Module 1.

===== FIN BLOC 2 =====
```

---

## Notes sur l'usage

### Si tu utilises GitHub

Avant de coller le bloc 1, dis à Claude Code :

> Je veux que ce projet soit hébergé sur mon GitHub `alysquart`. Crée d'abord un dépôt GitHub privé nommé `caneco-bt-tool` via l'API GitHub (`gh repo create alysquart/caneco-bt-tool --private`), puis configure le remote `origin` du dépôt local pour pointer vers ce dépôt distant. À chaque commit, push automatiquement.

Tu auras besoin d'avoir installé `gh` (GitHub CLI) et fait `gh auth login` au préalable.

### Si tu n'utilises pas GitHub

Tout fonctionne en local dans VS Code. Les commits restent dans le dossier `.git` du projet. Tu pourras pousser plus tard quand tu seras prêt.

### Si tu veux interrompre Claude Code

À tout moment tu peux taper `/stop` ou Ctrl+C pour interrompre. Pour reprendre, dis simplement « Continue où tu en étais ». Claude Code lit `CLAUDE.md` à chaque session pour récupérer le contexte.

### Si Claude Code te pose une question

Réponds simplement par un mot ou une phrase. Il continuera. Si la question concerne un choix structurant (ex. nom d'une variable), dis « Choisis ce qui te paraît le plus cohérent avec le PRD ». Il décidera et expliquera son choix.

---

**Fin du PROMPT_CLAUDE_CODE.md**
