# CLAUDE.md — Instructions projet

> Ce fichier est lu automatiquement par Claude Code à chaque session.
> Il contient le contexte projet, les conventions, et les garde-fous.
> **Ne pas modifier sans validation de l'équipe.**

---

## Identité du projet

- **Nom** : Valorisation des données CANECO BT
- **Cadre** : Challenge Innovation VEAO 2026
- **Agence** : Actemium Cegelec — VINCI Energies
- **Cas pilote** : projet DACHSER (Lot 3 — Électricité)
- **Stack** : Python / FastAPI / PostgreSQL / React / TypeScript / Tailwind / shadcn-ui / PWA

## Documents de référence (à consulter avant toute décision structurante)

- `docs/PRD.md` — Vision produit, personas, périmètre fonctionnel V1
- `docs/cahier_des_charges.md` — Spécifications fonctionnelles et techniques détaillées
- `docs/cartes_empathie.md` — Synthèse des trois personas (BE, Chef de Chantier, RA)
- `docs/brief_pitch.md` — Narratif de soutenance et prompts d'images

> **Avant de proposer une décision technique structurante (nouvelle dépendance, nouveau module, refonte d'un schéma de données), Claude Code lit le PRD et le cahier des charges pour vérifier que la décision est cohérente.**

---

## Style de code et conventions

### Principes généraux

1. **Code clair plutôt que clever**. Un développeur junior doit pouvoir reprendre le projet.
2. **Noms en français pour le métier, en anglais pour la technique**. Les entités du domaine (Projet, Tableau, Départ, Écart) sont nommées en français dans le modèle. Les couches techniques (HTTP, ORM, services) sont en anglais.
3. **Pas de magie**. Pas de monkey-patch, pas de méta-programmation, pas de décorateurs custom obscurs.
4. **Tests d'abord pour les règles métier critiques**. Le moteur de vérification, le parser CANECO et le générateur de DOE doivent avoir une couverture de tests > 80 %.

### Python (back-end)

- Python 3.11
- Formatage : **Black** (ligne max 100), **Ruff** pour le linting
- Imports triés avec **isort**
- Typage : **mypy strict** sur les modules de service métier
- Docstrings : style Google, en français pour les services métier

```python
def detecter_ecarts_section(
    ligne_caneco: CanecoLine,
    ligne_bordereau: BordereauLine | None,
) -> list[Gap]:
    """Détecte les écarts de section entre CANECO et bordereau.

    Args:
        ligne_caneco: Ligne issue de l'export CANECO BT.
        ligne_bordereau: Ligne du bordereau associée (None si non trouvée).

    Returns:
        Liste des écarts détectés. Vide si aucun écart.
    """
```

- Architecture : **routers / services / repositories**
  - `app/api/routers/` : endpoints FastAPI (validation Pydantic, appels services)
  - `app/services/` : logique métier (parsing, vérification, DOE)
  - `app/repositories/` : accès base de données (SQLAlchemy)
  - `app/models/` : modèles SQLAlchemy
  - `app/schemas/` : schémas Pydantic (DTO API)

### TypeScript (front-end)

- TypeScript 5.x, **strict** activé
- Formatage : **Prettier** (ligne max 100)
- Linting : **ESLint** avec `@typescript-eslint`
- Imports absolus avec alias `@/` (pointe sur `src/`)
- Composants : **PascalCase**, fichiers en `.tsx`
- Hooks custom : préfixe `use`, fichiers en `.ts`
- Pas de `any` non justifié (et alors avec un commentaire `// eslint-disable-next-line` + raison)
- Validation de formulaires : **react-hook-form + zod**

### Tailwind / shadcn

- Préférer les classes Tailwind aux styles inline
- Couleurs : utiliser les variables CSS définies dans `globals.css` (`--primary`, `--secondary`, `--vinci-red`, `--vinci-blue`)
- Espacements : utiliser l'échelle Tailwind par défaut (`p-2`, `gap-4`), éviter les valeurs arbitraires
- Composants : importer depuis `@/components/ui/...` (shadcn)

### Git

- Branche principale : `main` (protégée)
- Branches de travail : `feat/<description-courte>`, `fix/<description>`, `docs/<description>`
- Messages de commit : **Conventional Commits**
  - `feat: ajout du parser CANECO`
  - `fix: corriger le rapprochement bordereau quand le repère est tronqué`
  - `docs: compléter le README`
  - `chore: mise à jour des dépendances`
  - `test: ajout des cas de recette du moteur de vérification`
- Un commit = une intention claire. Pas de gros commits fourre-tout.

---

## Garde-fous absolus

Ces règles ne sont jamais violées, sans exception. Si une instruction utilisateur contredit l'une d'elles, Claude Code demande confirmation.

1. **Ne jamais hardcoder de secret** dans le code source. Tout secret (clé API, mot de passe DB, JWT secret) passe par variable d'environnement, lue via `pydantic-settings`.
2. **Ne jamais committer de fichier `.env`**. Le `.gitignore` l'exclut. Un fichier `.env.example` est commité comme template.
3. **Ne jamais désactiver une vérification de sécurité** (CORS, CSRF, validation Pydantic, hashage bcrypt) sans validation explicite et trace dans le code.
4. **Ne jamais supprimer ni écraser** un fichier dans `data/seed/` (notamment les fichiers DACHSER de référence).
5. **Ne jamais introduire de dépendance non listée** dans le PRD ou le cahier des charges sans documenter le choix dans le `CHANGELOG.md` du projet.
6. **Ne jamais inventer une donnée** (chiffre, métrique, fait métier) qui ne soit pas explicitement dans les sources du projet.
7. **Pas d'emoji dans le code, les commentaires, les commits, les UI utilisateur**. Le projet est destiné à un environnement professionnel VINCI.

---

## Règles de sécurité à appliquer dès l'écriture du code

Ces règles doivent être appliquées **systématiquement** pendant le développement, pas uniquement lors de l'audit final. Elles couvrent les vulnérabilités les plus fréquentes dans les projets « vibe-codés » avec des assistants IA.

Le détail complet est dans `SECURITY_AUDIT_PROMPT.md`. Voici les règles d'écriture :

### Secrets et configuration

- Toute valeur sensible passe par `pydantic-settings`. Aucun `os.environ.get(...)` direct dans la logique métier.
- `JWT_SECRET_KEY` doit faire au moins 32 caractères aléatoires. Si la valeur de configuration est `"changeme"` ou `"secret"`, l'application doit refuser de démarrer.
- Aucune clé sensible (`ANTHROPIC_API_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`) ne doit être préfixée `VITE_` ni accessible côté client.
- Aucun `console.log`, `console.error`, `print()` ne doit afficher un objet `User` complet, un token, une clé d'environnement, ou un payload contenant un mot de passe.

### Authentification et autorisation

- Chaque route protégée utilise `Depends(get_current_user)`. Aucune route protégée n'est créée sans cette dépendance.
- L'identité utilisateur pour les opérations d'écriture vient **toujours** du token, **jamais** d'un champ `user_id` du body de requête.
- Pour chaque endpoint qui prend un identifiant en paramètre (`/projects/{id}`, `/gaps/{id}`), une vérification explicite que l'utilisateur courant a bien accès à cette ressource est faite avant tout traitement.
- Les schémas Pydantic d'entrée (POST/PATCH) **n'acceptent pas** les champs `id`, `user_id`, `created_at`, `is_admin`, `role`. Pour les contrôler, utiliser `model_config = ConfigDict(extra="forbid")`.
- Les mots de passe sont hashés avec bcrypt, coût >= 12.

### Validation des entrées

- Toute route reçoit ses entrées via des modèles Pydantic, jamais via `Request.json()` brut.
- Les uploads de fichiers (CANECO Excel, bordereau, CPS PDF) :
  - Vérifient le type MIME côté serveur (pas l'extension)
  - Appliquent une taille maximale (50 Mo Excel, 100 Mo PDF)
  - Sont stockés dans `data/uploads/<project_id>/`, jamais dans un dossier servi statiquement
  - Sont parsés avec des bibliothèques qui ne chargent pas les macros (`openpyxl` plutôt que `xlwings`)

### Base de données

- Aucune requête SQL brute avec interpolation directe. Utiliser systématiquement les bind params SQLAlchemy.
- Aucune route ne retourne toutes les lignes d'une table sans filtrage par utilisateur ou par rôle.
- Aucune migration Alembic ne contient de DDL destructif sans validation explicite.

### Routes publiques

La route `GET /t/<token>` (fiche tableau accessible par scan QR) est la **seule** route publique non authentifiée.

- Le token est généré par `secrets.token_urlsafe(32)` (au moins 24 caractères).
- Le token ne contient ni l'ID du projet ni l'ID du tableau (donc imprévisible).
- La route est en lecture seule. Aucune modification n'est possible via ce token.
- La réponse ne contient que les informations strictement nécessaires à l'affichage de la fiche, pas le projet complet ni les données client autres que le repère du tableau.

### CORS et déploiement

- `CORSMiddleware` est configuré avec `allow_origins=["http://localhost:5173"]` en dev (liste explicite, jamais `["*"]`).
- `allow_credentials=True` n'est associé qu'à des origines spécifiques.
- `allow_headers` est limité à `["Authorization", "Content-Type"]`.

### Logs

- Les logs serveur ne contiennent jamais le contenu intégral des fichiers uploadés ni les saisies chantier complètes.
- Logger uniquement les métadonnées (nom du fichier, taille, user_id, project_id, timestamp).
- En production, le handler d'exception global retourne `"Internal server error"` au client et logue le détail côté serveur uniquement.

### Rate limiting

- Endpoints `POST /api/auth/login` et `POST /api/auth/register` : limitation de débit obligatoire (slowapi en V1, Redis en V2).
- Endpoints qui appellent l'API LLM Anthropic : limitation stricte par utilisateur pour éviter une explosion de la facture.

### Avant chaque tag de version

Avant de créer un tag (`v0.1.0`, `v0.2.0`, ...), Claude Code applique le **prompt d'audit complet** disponible dans `SECURITY_AUDIT_PROMPT.md`. Aucune conclusion CRITIQUE ne doit rester ouverte au moment du tag.

---

## Données de test

Le projet contient un dataset de référence pour DACHSER, sous `data/seed/dachser/` :

- `DATA_DACHSER_INDICE_B.XLS` — export CANECO BT, indice B (700 lignes, 23 colonnes)
- `Pièce_03_Bordereau_des_Prix_DACHSER_LOT3.xlsx` — bordereau de prix (244 lignes utiles dans la feuille « BDP_ELECTRICITE CFO »)
- `Pièce_021_Clauses_techniques_DACHSER_LOT3.pdf` — CPS du projet
- `Pièce_02-2_Descriptif_des_ouvrages_DACHSER_LOT3.pdf` — descriptif des ouvrages

Toutes les fonctions de parsing et de vérification doivent passer sans erreur sur ces fichiers de référence. Un test d'intégration `tests/integration/test_dachser_pipeline.py` valide que l'enchaînement complet (upload CANECO → parsing → vérification → rapport d'écarts) produit un nombre d'écarts cohérent.

---

## Architecture haut niveau

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routers/       # Endpoints FastAPI
│   │   │   └── deps.py        # Dépendances (auth, db session)
│   │   ├── core/
│   │   │   ├── config.py      # Settings (pydantic-settings)
│   │   │   ├── security.py    # JWT, password hashing
│   │   │   └── logging.py     # Configuration loguru
│   │   ├── db/
│   │   │   ├── base.py        # Base SQLAlchemy
│   │   │   └── session.py     # Session factory
│   │   ├── models/            # Modèles SQLAlchemy
│   │   ├── schemas/           # Schémas Pydantic (DTO)
│   │   ├── services/          # Logique métier
│   │   │   ├── caneco/        # Parser CANECO
│   │   │   ├── bordereau/     # Parser bordereau
│   │   │   ├── cps/           # Parser CPS
│   │   │   ├── verification/  # Moteur de vérification
│   │   │   ├── doe/           # Générateur DOE
│   │   │   ├── qr/            # Génération QR codes
│   │   │   └── llm/           # Adapter LLM optionnel
│   │   ├── repositories/      # Accès données
│   │   └── main.py            # Point d'entrée FastAPI
│   ├── alembic/               # Migrations DB
│   ├── tests/                 # Tests pytest
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Composants React
│   │   │   ├── ui/            # shadcn-ui (généré)
│   │   │   └── ...            # Composants métier
│   │   ├── pages/             # Pages (router)
│   │   ├── hooks/             # Hooks custom
│   │   ├── lib/               # Utilitaires
│   │   ├── api/               # Client API (axios + react-query)
│   │   ├── types/             # Types TypeScript partagés
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                      # Documentation projet
│   ├── PRD.md
│   ├── cahier_des_charges.md
│   ├── cartes_empathie.md
│   └── brief_pitch.md
│
├── data/
│   └── seed/
│       └── dachser/           # Fichiers de référence
│
├── docker-compose.yml         # Postgres + back + front en dev
├── README.md                  # Démarrage rapide
├── CLAUDE.md                  # Ce fichier
└── .env.example
```

---

## Workflow Claude Code recommandé

1. **Comprendre avant de coder**. Avant toute tâche structurante, Claude Code lit le PRD et le cahier des charges. Si un point n'est pas clair, il pose la question plutôt que d'inventer.
2. **Découper en petites étapes**. Une tâche = un commit. Si la tâche dépasse 20 fichiers modifiés, Claude la propose en plusieurs sous-tâches.
3. **Tester systématiquement**. Une nouvelle fonction métier vient avec son test pytest (ou Vitest côté front).
4. **Documenter dans le code**. Les services métier ont des docstrings en français. Les fichiers de configuration ont un en-tête expliquant leur rôle.
5. **Mettre à jour le CHANGELOG.md** à chaque feature.
6. **Privilégier la simplicité**. En cas de doute, choisir la solution la plus simple qui résout le besoin V1.

---

## Commandes utiles

```bash
# Démarrer l'environnement complet
docker compose up -d

# Back-end : tests
cd backend && pytest

# Back-end : lancer le serveur en dev (hors docker)
cd backend && uvicorn app.main:app --reload

# Back-end : migration
cd backend && alembic upgrade head

# Front-end : dev server
cd frontend && pnpm dev

# Front-end : build production
cd frontend && pnpm build

# Front-end : tests
cd frontend && pnpm test
```

---

## Notes sur l'agent IA

L'agent intelligent **n'est pas une boîte noire LLM**. Il est composé de :

1. Un **moteur de règles déterministe** (codé en Python pur), qui couvre 95 % des cas.
2. Une **couche LLM optionnelle** (API Claude) pour les cas non structurés (extraction de règles depuis un CPS PDF désordonné, formulation d'écarts en langage naturel).

Le moteur déterministe est la **source de vérité** des écarts. Le LLM ne peut **jamais** invalider un écart détecté par le moteur. Il peut uniquement :
- Suggérer des écarts supplémentaires (toujours marqués comme « à confirmer »)
- Reformuler le libellé d'un écart pour le rendre plus lisible
- Extraire des règles depuis un CPS PDF non structuré (toujours validées ensuite par les règles déterministes)

Si l'API Claude n'est pas configurée (clé absente dans `.env`), l'outil fonctionne en mode 100 % déterministe sans dégradation des fonctions critiques.

---

## Que faire si je détecte une incohérence

Si Claude Code détecte une incohérence entre :
- Une instruction utilisateur et le PRD
- Le PRD et le cahier des charges
- Un comportement attendu et le code existant

Il **arrête la tâche en cours**, signale l'incohérence à l'utilisateur, et propose deux options :
1. Mettre à jour le document de référence
2. Adapter l'instruction

Il ne tranche jamais seul.

---

**Fin du CLAUDE.md**
