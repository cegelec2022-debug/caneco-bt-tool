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

## Rapport PFE LaTeX — consignes maîtresses

> Cette section pilote la rédaction du rapport de Projet de Fin d'Études.
> Elle est lue à chaque session de rédaction et reste à jour entre les chapitres.

### Identité du rapport (CONFIRMÉ 18/06/2026)

- **Titre officiel école (à conserver tel quel)** : *Étude et dimensionnement réseau thermique, électrique d'une unité industrielle et logistique*
- **Auteur** : Aly Aly SANOH
- **Filière** : Génie Électrique et Management Industriel (GEMI), 3ᵉ année cycle ingénieur
- **Établissement** : Université Abdelmalek Essaâdi — Faculté des Sciences et Techniques de Tanger (FSTT) — Département de Génie Électrique
- **Entreprise d'accueil** : Actemium / Cegelec Tanger — VINCI Energies Maroc
- **Encadrante entreprise** : Mme Mariam JIBRANE
- **Encadrants académiques FST** : Pr. M. BOULAALA / Pr. Z. MEKRINI (deux encadrants académiques)
- **Jury de soutenance** :
  - Pr. **Mohamed Yamni** — Président
  - Pr. **Mohamed El Harzli** — Rapporteur
  - Pr. **M'hamed El Mrabet** — Rapporteur
  - Pr. Boulaala / Pr. Mekrini — Encadrants FST
  - Mme Mariam Jibrane — Encadrante Entreprise
- **Soutenance** : **02 juillet 2026, 12 h, salle C03**
- **Dépôt rapport** : 26 juin 2026 (papier + PDF + CD + version après soutenance)
- **Volume rapport** : 60 pages max, grand max 65 hors annexes (consigne FST)
- **Statut au 18/06/2026** : version finale prête à envoyer aux encadrants académiques (89 pages totales, 67 corps)

### Consignes école (verbatim — avis Pr. BSISS)

- 60 pages maximum hors annexes
- Police Times New Roman 12 pt (équivalent LaTeX accepté : Linux Libertine)
- Interligne 1,5
- Marges standards (left 3 cm, right/top/bottom 2,5 cm)
- Numérotation pages, mise en forme soignée
- Page de garde selon modèle GEMI fourni
- Sommaire, introduction, conclusion, références bibliographiques obligatoires
- Listes : figures, tableaux, abréviations obligatoires
- **5 exemplaires** papier reliure spirale + CD + rapport après soutenance (5 car deux encadrants académiques)

### Localisation des ressources

Tout est sous `C:\Users\hp\Desktop\Ressources_PFE_VINCI\` (créé en juin 2026) :

```
00_Consignes_Ecole/             Page de garde GEMI (modèle officiel)
01_Rapports_Inspiratifs/
  ├── Capgemini/                Rapport PFA ADAS (auteur) — base structure et LaTeX
  ├── CFA_CFO_BIM/              28 rapports anciens étudiants même domaine
  └── Machine_Learning/         Rapport inspiratif ML
02_Rapports_Anciens_Etudiants/  Rapport_Stage V2 (étudiant photovoltaïque)
03_Mes_Rapports_Avancement/     3 rapports d'avancement PDF + 2 DOCX (réf. travaux Phase 1 à 5)
04_VINCI_Identite_Marque/       Logos, charte, infos web VINCI Energies (à enrichir)
05_Projet_DACHSER/              Gantt, PPT, CCTP, plans, Revit, BP, fiches CFO/CFA
06_Outil_Bilan_Puissance_VBA/   BP 0 macro.xlsm + modules .bas (outil VBA développé)
07_Outil_CANECO_Valorisation/   Vidéo démo + Innovation VEAO 2026 (carte empathie, PPT pitch)
08_Photos_Chantier/             Photos WhatsApp chantier DACHSER
09_Template_Latex_HPI/          Template thesis.tex de référence (Libertine + newtxmath)
99_Rapport_PFE_Latex/           DOSSIER DE TRAVAIL — main.tex + chapitres + figures + bib
```

### Décisions techniques figées

| Aspect | Décision |
|---|---|
| Moteur | MikTeX 25.12 (`pdflatex` local) |
| Classe document | `report`, 12pt, A4, oneside (le rapport est imprimé une face) |
| Police texte | `\usepackage{libertine}` (Linux Libertine — Times-like, x-height généreux) |
| Police maths | `\usepackage[libertine]{newtxmath}` |
| Interligne | `\onehalfspacing` (1,5) |
| Géométrie | `left=3cm, right=2.5cm, top=2.5cm, bottom=2.5cm` |
| Encodage | UTF-8 (`inputenc`) + T1 (`fontenc`) + `babel` français |
| Langue | Français pour le corps, abstract anglais en plus du résumé |
| Couleur primaire | `vinciRed` RGB(227,30,36) — bandeau page de garde, titres chapitres |
| Couleur secondaire | `vinciNavy` RGB(0,47,86) — sections, sous-titres |
| Couleur accent | `actemiumGreen` RGB(0,153,60) — encadrés métier, tableaux |
| Reste | Niveaux de gris uniquement. Pas de couleur décorative. |
| Hyperliens | `hyperref` actif pour table des matières, listes, citations — cliquables dans le PDF |
| Pages landscape | UNIQUEMENT pour le WBS (forest) et le diagramme de Gantt (pgfgantt) via `pdflscape` |
| Cadre page de garde | TikZ : double cadre `vinciRed` (extérieur) + `vinciNavy` (intérieur), inspiré Capgemini |

### Plan validé (6 chapitres — chap7 supprimé, tests intégrés au chap6)

- **Pages préliminaires** : page de garde, dédicaces, remerciements, résumé/abstract, TOC, listes figures/tableaux/abréviations
- **Introduction générale**
- **Chapitre 1** — Présentation générale et contexte du projet (VINCI Energies / Actemium / Cegelec, 6 marques avec sous-sections individuelles préservées, projet DACHSER, plan réseau extérieur, problématique, objectifs, méthodologie, WBS landscape + Gantt landscape, risques)
- **Chapitre 2** — État de l'art : conception électrique BT et outils métiers (NFC 15-100, bilan de puissance, CANECO BT, BIM électrique, sprinklage NFPA 13)
- **Chapitre 3** — Dimensionnement BT DACHSER (positionnement bilan dans processus CFO VINCI, synoptique MT/BT, table REP officielle 24 lignes, formules par circuit en français sans `=SUMIF`, agrégation TGBT 663,34 kVA / 800 kVA / 17,08% réserve, plans chemins de câbles + 4 fiches étapes pose 2 par 2)
- **Chapitre 4** — Modélisation BIM réseau sprinklage Revit (cadre normatif, paramétrage, état d'avancement : setup + tracés préliminaires, **PAS de maquette LOD350 livrée**, contraintes matérielles documentées, vues 3D Dialux illustratives avec caption HONNÊTE)
- **Chapitre 5** — Outil VBA bilan de puissance (architecture en 3 zones, logique calcul, formules trigonométriques, cas canalisations préfabriquées, choix calibre transfo avec règle 15% marge, catalogue 431 équip., validation contre bilan officiel)
- **Chapitre 6** — Outil CANECO BT (Challenge VEAO 2026, V1 18/06/2026, 3 briques, architecture simplifiée sans jargon, 14 captures écrans réels DACHSER+NSK, validation E-004, métriques PRD)
- **Conclusion générale et perspectives**
- **Bibliographie / Webographie**
- **Annexes** : A) arborescence projet outils (PAS de code, juste structure dossiers), B) captures supplémentaires, C) liens démo, D) glossaire technique

### Style éditorial — règles absolues

1. **Ton humain, professionnel, sobre**. Pas de tournures « IA » (« Il est important de noter que », « Comme nous l'avons vu précédemment », etc.). Pas de phrases auto-référentielles vers le rapport (« ce rapport montre que », préférer la voix passive métier).
2. **Pas de superlatifs auto-élogieux**. Bannis : *expertise*, *largement supérieur au marché*, *innovation disruptive*, *excellence technique*. Préférer : *les résultats obtenus*, *cohérent avec*, *adapté au besoin métier*.
3. **Pas d'instructions de méta-rédaction** dans le texte (« nous allons voir », « passons maintenant à »). Le lecteur sait lire — la table des matières fait le travail.
4. **Formules mathématiques** systématiquement accompagnées de la signification des symboles, dans un environnement `equation` numéroté. Exemple : après chaque formule, lister `où : P = puissance installée (kW), Ku = coefficient d'utilisation, Ks = coefficient de simultanéité`.
5. **Toutes formules NFC 15-100, méthode CANECO, hydraulique NFPA 13, ML (si évoqué)** sont citées avec la source (norme, document de référence). Pas de formule « tombée du ciel ».
6. **Illustrations** : chaque figure/tableau a une légende ET est référencée dans le texte (`comme illustré sur la Figure~\ref{...}`). Pas de figure orpheline.
7. **Hyperliens cliquables** : TOC, liste figures, liste tableaux, citations bibliographiques, URLs — tout doit être cliquable dans le PDF (via `hyperref`).
8. **Pas d'emoji**. Jamais. Même pas dans les notes ou TODO LaTeX.
9. **Pas de couleurs hors charte VINCI**. Niveaux de gris pour le reste. Justifier toute couleur ajoutée.

### Convention images

- Toutes les images vont dans `99_Rapport_PFE_Latex/figures/`
- Nom de fichier en **kebab-case** : `logo-vinci-energies.png`, `wbs-pfe-dachser.pdf`, `dashboard-canecotool-vue-ra.png`
- Format : **PNG** pour captures et photos, **PDF** ou **SVG** pour schémas vectoriels (TikZ exporté), **JPG** uniquement si déjà en JPG (photos chantier WhatsApp)
- Résolution minimale : **300 dpi** pour impression
- Lorsqu'une image est à fournir par l'auteur, je laisse un commentaire LaTeX `% TODO IMAGE: <nom-exact-attendu>.png — <description précise de ce qu'il faut capturer/télécharger>` et je liste dans le récap fin de chapitre tout ce qui manque

### Workflow chapitre par chapitre

1. Avant chaque chapitre, je relis les ressources concernées (un rapport inspiratif sur ce thème + section pertinente du Capgemini + ressource métier).
2. Je propose **le plan détaillé** du chapitre (sections, sous-sections, figures prévues) avant rédaction.
3. L'utilisateur valide ou ajuste.
4. Je rédige le `.tex` du chapitre, je compile via `pdflatex` en local, je rends compte des warnings.
5. L'utilisateur relit le PDF, je corrige.
6. Passage au chapitre suivant.

### Prompt ultim rapport — VINCI/Actemium PFE (adapté du prompt Capgemini PFA de l'auteur)

> Ce prompt est la **consigne maîtresse** réutilisée à chaque session de rédaction. Il transpose le prompt Capgemini PFA que l'auteur a utilisé pour son rapport ADAS (`Drive edu uiz/Cap PFA-/Cap PFA/Capgemini Eng/Prompts.txt`), adapté au sujet VINCI/Actemium et à la nature dual-outil (BP VBA + Outil CANECO) de ce PFE.

**Inspirations sources** (à relire avant chaque chapitre concerné) :

- `01_Rapports_Inspiratifs/Capgemini/Rapport/Rapport inspiratif capgemini Engineering.docx` — modèle de **structure du plan**, de **ton professionnel**, et présentation organisme d'accueil. Les chiffres et descriptions Capgemini sont remplacés par les chiffres VINCI Energies et Actemium/Cegelec.
- `01_Rapports_Inspiratifs/Machine_Learning/Rapport inspiratif ML.pdf` — modèle pour **expliquer un concept technique** avant son application (utile pour chapitres 2, 5, 6 : tout concept est d'abord posé — NFC 15-100, bilan de puissance, CANECO BT, architecture API REST, sécurité JWT — AVANT d'être appliqué au cas DACHSER).
- `01_Rapports_Inspiratifs/CFA_CFO_BIM/` — 28 rapports anciens étudiants même domaine : ressources pour vocabulaire métier, présentations CCTP, schémas unifilaires, tableaux de bilan de puissance type.

**Règles de ton — sans exception** :

1. **Ton humain, pro, sobre et naturel.** Pas de tournures « IA » (« il est important de noter », « comme nous l'avons vu », « ce chapitre nous montrera »). Le lecteur sait lire — la table des matières fait le travail.
2. **Pas d'auto-positionnement « expert ».** Bannis : *expertise*, *largement supérieur au marché*, *innovation disruptive*, *excellence technique*, *bien au-delà des standards*. Préférer factuel : *les résultats obtenus*, *cohérent avec*, *conforme au CCTP*, *écart de 0 kW vis-à-vis du bilan officiel*.
3. **Pas de méta-commentaire** sur le rapport lui-même (« dans ce qui suit nous verrons »). Le texte parle directement au lecteur.
4. **Voix passive métier ou je sobre.** Pas de « nous » académique creux.

**Formules mathématiques et physiques** :

- Toute formule est posée dans un environnement `equation` numéroté.
- Juste après l'équation, lister les symboles : `où : Pi = puissance installée (kW), Ku = coefficient d'utilisation, Ks = coefficient de simultanéité (NF C 15-100 §4.2)`.
- Source citée (norme NF C 15-100 / 13-200, guide UTE, méthode CANECO, NFPA 13 pour sprinklage, etc.).
- Pour le bilan de puissance, formules implémentées dans `06_Outil_Bilan_Puissance_VBA/BP 0 macro.xlsm` (rapport avancement n°3 §2.3) :
  - Par circuit : `Ptot = Nrec × Napp × Pu × Ku × Ks`
  - Par tableau : `Pfois = Kf × Σ Ptot`, `Pinstall = (1+r) × Pfois` avec r = 20 %
  - Conversion kVA : `S = P / cosφ_moyen pondéré`

**Convention images — exécution stricte** :

- Toutes images dans `99_Rapport_PFE_Latex/figures/`, nom en **kebab-case**.
- Format : PNG (captures, photos), PDF/SVG (schémas vectoriels TikZ), JPG (uniquement WhatsApp originales).
- Résolution mini 300 dpi.
- Quand l'auteur doit fournir une image : commentaire LaTeX explicite et récap fin de chapitre :
  ```latex
  % TODO IMAGE: dashboard-canecotool-ra-overview.png
  % Capture demandée : se connecter en tant que RA, ouvrir le dashboard global,
  % zoomer sur la barre de KPI + carte projet DACHSER, plein écran navigateur,
  % résolution 1920x1080. Format PNG.
  \begin{figure}[H]
      \centering
      \includegraphics[width=0.95\textwidth]{figures/dashboard-canecotool-ra-overview.png}
      \caption{Dashboard global du Responsable d'Affaires — outil de valorisation CANECO BT}
      \label{fig:dashboard-canecotool-ra-overview}
  \end{figure}
  ```
- Pour les **captures vidéo démo CANECO** (`07_Outil_CANECO_Valorisation/Video demo*.mp4`) : je nommerai chaque capture précisément (ex. `canecotool-login.png`, `canecotool-tableaux-liste.png`, `canecotool-fiche-publique-qr.png`, `canecotool-saisie-chantier.png`, `canecotool-stock-alerte.png`, `canecotool-dashboard-ra.png`), l'auteur prend la capture à l'instant indiqué de la vidéo, l'enregistre sous ce nom dans `figures/`, l'image apparaît automatiquement à la compilation.
- Pour les **logos / illustrations standard** (logo VINCI Energies, Actemium, Cegelec, Excel, VBA, Python, FastAPI, React, PostgreSQL, Revit, AutoCAD, normes NF…) : je donne la requête Google précise (ex. `"VINCI Energies logo SVG transparent fond blanc"`) + le nom de fichier exact à utiliser dans `figures/`. Privilégier Wikimedia Commons ou sites officiels (haute résolution, libre de droits).
- Pour les **schémas conceptuels** (architecture outil, flux de données, schéma unifilaire générique, organigramme Actemium, WBS, Gantt) : je les fais en **TikZ pro** directement dans le `.tex` — pas besoin de fichier image externe.

**Code source** :

- **Pas de code dans les chapitres principaux**. Ce serait écrasant.
- En annexe : **arborescence des projets** (BP VBA + Outil CANECO) sous forme d'arbre `forest` ou `dirtree`, **liens GitHub privés** ou **lien Drive** vers le repo, **liens démo** (tunnel ngrok pour CANECO).
- Si un extrait court est indispensable (formule VBA clé, route FastAPI emblématique) : 5-10 lignes max, environnement `lstlisting` minimaliste, en gris discret, jamais coloré.

**Diagrammes** :

- Pas tous les diagrammes UML/SysML — seulement les **nécessaires** :
  - Chapitre 1 : WBS (forest, landscape), Gantt (pgfgantt, landscape) — code à intégrer depuis `05_Projet_DACHSER/5e_Planning_Gantt/`
  - Chapitre 3 : schéma unifilaire simplifié TGBT DACHSER (TikZ)
  - Chapitre 5 : architecture outil BP VBA (TikZ blocs : Saisie → Catalogue → Tableaux → Circuits → Génération → Bilan → Export PDF)
  - Chapitre 6 : architecture C4 niveau 2 outil CANECO (TikZ : React frontend / FastAPI backend / PostgreSQL / tunnel ngrok), diagramme de séquence scan QR fiche publique
- Toute page WBS ou Gantt **doit être en landscape** via `pdflscape` — non négociable, sinon illisible.

**Couleurs — usage strict** :

- `vinciRed` `RGB(227,30,36)` — uniquement bandeau page de garde, double trait décoratif chapitres, cadre encart définition
- `vinciNavy` `RGB(0,47,86)` — titres chapitres, sections
- `actemiumGreen` `RGB(0,153,60)` — encadrés métier rares (max 2-3 dans tout le rapport)
- Le reste : gris (`gray!60`, `gray!30`) ou noir. Aucune autre couleur introduite sans justification.

**Listes obligatoires (hyperlinks cliquables via `hyperref`)** :

- Table des matières
- Liste des figures
- Liste des tableaux
- Liste des abréviations (table 2 colonnes : acronyme | signification, ordre alphabétique)
- Bibliographie (BibTeX, `biber`)
- Tous les renvois `\ref{...}` et `\cite{...}` sont cliquables dans le PDF final.

**Packages LaTeX à charger dès le chapitre 1** (pour ne plus y revenir) :

```latex
% Encodage et langue
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}

% Police Libertine + maths newtx
\usepackage{libertine}
\usepackage[libertine]{newtxmath}
\usepackage{microtype}

% Géométrie + interligne
\usepackage{geometry}
\geometry{left=3cm, right=2.5cm, top=2.5cm, bottom=2.5cm}
\usepackage{setspace}
\onehalfspacing

% Maths
\usepackage{amsmath, amssymb, amsfonts, mathtools}
\usepackage{siunitx}  % unités SI (kW, kVA, kHz, etc.)

% Tableaux et figures
\usepackage{graphicx}
\usepackage{float}
\usepackage{tabularx, booktabs, multirow, multicol, longtable}
\usepackage{caption, subcaption}
\usepackage{wrapfig}

% TikZ et diagrammes
\usepackage{tikz}
\usepackage{pgfgantt}
\usepackage{forest}
\usetikzlibrary{shapes.geometric, arrows, positioning, decorations.pathmorphing, shadows, calc, fit, backgrounds}

% Landscape WBS + Gantt
\usepackage{pdflscape}

% Mise en forme
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{enumitem}
\usepackage{xcolor}
\definecolor{vinciRed}{RGB}{227,30,36}
\definecolor{vinciNavy}{RGB}{0,47,86}
\definecolor{actemiumGreen}{RGB}{0,153,60}
\definecolor{proGray}{RGB}{64,64,64}

% Code (rare, en annexe)
\usepackage{listings}

% Hyperliens (toujours en dernier ou presque)
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=vinciNavy,
    citecolor=vinciNavy,
    urlcolor=vinciRed,
    pdftitle={Étude et dimensionnement réseau BT DACHSER \& valorisation des données CANECO BT},
    pdfauthor={Aly Aly SANOH},
    pdfsubject={Rapport PFE — VINCI Energies / Actemium Cegelec Tanger},
    pdfkeywords={CANECO BT, Bilan de puissance, NFC 15-100, DACHSER, FastAPI, React, VBA, BIM, sprinklage, VINCI Energies}
}
```

**Lien Drive vidéo démo** : l'auteur fournira un lien Drive vers la vidéo démo de l'outil CANECO BT, à insérer dans la conclusion + annexes.

**Workflow chapitre par chapitre — non négociable** :

1. **Plan détaillé** du chapitre proposé en premier (sections, sous-sections, figures prévues avec noms exacts attendus).
2. Validation auteur.
3. Rédaction du `.tex` du chapitre.
4. Compilation locale via `pdflatex` (MikTeX), rendre compte warnings.
5. Récap fin de chapitre : liste exacte des images à fournir/télécharger/capturer avec instructions précises (nom de fichier, source, requête Google si web).
6. Relecture auteur du PDF généré.
7. Corrections.
8. Passage au chapitre suivant uniquement après validation.

### Récap des trois rapports d'avancement (lus, à recycler)

Couvrent les Phases 1-5 du PFE (Février → Avril 2026), AVANT l'amorce de l'outil CANECO BT :

- **N°1** (mars 2026) : formation, intégration, premier contact projet
- **N°2** (15-04-2026) : amorce outil BP VBA, modélisation BIM sprinklage Revit
- **N°3** (30-04-2026) : outil BP VBA v2 livré, validation contre bilan CEGELEC officiel (596,15 kW Δ=0, 17/20 tableaux conformes), visite chantier HSE + entretiens chef équipe électrique & fluide, instruction métier à mettre à jour

Deux rapports d'avancement supplémentaires (n°4 + n°5) couvriront le développement de l'outil CANECO BT — à rédiger dans le même format.

### Chiffres officiels à utiliser dans le rapport (validés par rapport n°3)

- Outil BP : catalogue **465 équipements / 45 catégories**, **22 tableaux**, **457 circuits**, ≈ **30 procédures VBA**
- Validation TGBT DACHSER : **596,15 kW** (Δ=0), **476,92 kW foisonnée** (Δ=0), **572,30 kW installée** (Δ=0), **663,33 kVA souscrite**, **calibre 800 kVA**, **réserve 17,08 %**
- Cohérence : **17 tableaux divisionnaires conformes / 20** ; 3 anomalies documentées (TES1, TES2, TCFA) — convention N&NS à raffiner en v3
- Outil testé aussi sur **projet NSK** de l'agence



### État courant (mis à jour à chaque session)

- [x] Phase 1 — Organisation ressources (Ressources_PFE_VINCI créé, ~120 fichiers copiés)
- [x] Phase 2 — Lecture template HPI thesis.tex (Libertine confirmé)
- [ ] Phase 3 — Lecture rapports avancement + BP VBA + 1-2 inspiratifs CFA-CFO-BIM
- [ ] Phase 4 — Recherche web VINCI Energies (logos HD, chiffres 2024-2025, marques)
- [ ] Phase 5 — Squelette `main.tex` + page de garde + chapitre 1
- [ ] Phase 6 — Chapitres 2 à 7 (un par session validée)
- [ ] Phase 7 — Bibliographie, annexes, relecture finale

---

**Fin du CLAUDE.md**
