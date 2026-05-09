# SECURITY_AUDIT_PROMPT.md — Audit de sécurité de la V1

> **Quand utiliser ce fichier** : à coller dans Claude Code à la fin du Module 6 (juste avant le tag `v0.1.0`) et avant chaque release majeure.
>
> Ce prompt est une **adaptation du prompt d'audit générique « vibe-codé »** à la stack exacte de ce projet : FastAPI + PostgreSQL + React + TypeScript + JWT + PWA, hébergé en local Docker pour la V1.
>
> Les sections concernant Supabase, Next.js, Firebase ont été retirées ou remplacées. Les sections critiques pour notre contexte (CORS local, JWT, parsing de fichiers Excel/PDF) ont été renforcées.

---

## Pourquoi cet audit est important

L'outil traite des données de projets clients VINCI (CPS, bordereaux, plans). Une fuite de données ou une compromission de l'instance pilote ferait :
1. Perdre la confiance du sponsor et des autres agences
2. Compromettre l'extension à d'autres projets et au Groupe
3. Affecter la perception de l'innovation IA chez VINCI Energies BT

C'est précisément parce que cette V1 a été en partie « vibe-codée » avec Claude Code que cet audit est obligatoire. Le code fonctionne probablement, mais les failles classiques (secrets en dur, validation manquante, CORS large) doivent être levées avant tout déploiement, même pilote.

---

## À coller dans Claude Code

Copie tout ce qui se trouve **entre les deux lignes `===== DÉBUT PROMPT =====` et `===== FIN PROMPT =====`** (sans inclure ces deux lignes), et colle-le dans Claude Code à la racine du projet `caneco-bt-tool`.

Claude Code va lire l'intégralité du code, dérouler l'audit, et te livrer un rapport structuré.

```
===== DÉBUT PROMPT =====

<role>
Tu effectues un audit de sécurité complet de l'application "Valorisation des données CANECO BT".

Cette application a été en grande partie construite avec ton aide (Claude Code) en mode "vibe-codé" : elle est fonctionnelle, mais peut contenir des failles classiques que les assistants IA introduisent régulièrement (secrets en dur, validation manquante, CORS large, expositions de données).

Ton travail est de trouver chacune de ces failles et de les corriger.

# Stack technique de référence

- **Back-end** : Python 3.11 + FastAPI + SQLAlchemy 2 + Alembic
- **Base de données** : PostgreSQL 16 (PAS Supabase, PAS Firebase — base de données traditionnelle côté serveur uniquement)
- **Authentification** : JWT (python-jose) avec hash bcrypt (passlib)
- **Front-end** : React 18 + Vite + TypeScript + TailwindCSS + shadcn/ui
- **Déploiement V1** : Docker Compose en local sur poste développeur ; en V2 prévu sur Render/Fly.io plan free
- **API LLM optionnelle** : Anthropic Claude (clé en env, peut être absente)
- **Données sensibles** : fichiers projets clients VINCI (CPS, bordereaux, plans, exports CANECO BT)
</role>

<methodology>

# PASSE 1 — DÉCOUVERTE

Lis l'intégralité de la base de code avant de produire des conclusions :
- Structure des dossiers `backend/` et `frontend/`
- `docker-compose.yml`
- Toutes les routes FastAPI (`backend/app/api/routers/`)
- Configuration (`backend/app/core/config.py`, `.env.example`)
- Modèles SQLAlchemy et migrations Alembic
- Composants front-end qui touchent à l'authentification et aux uploads
- Le `.gitignore`
- L'historique git (au moins les 30 derniers commits)

Construis un modèle mental de l'architecture et trace le flux des données depuis l'entrée utilisateur (upload de fichier, formulaire, scan QR, requête API) jusqu'à la base de données et retour.

# PASSE 2 — AUDIT SYSTÉMATIQUE

Pour chaque élément de la checklist ci-dessous, produis exactement un des verdicts suivants :

- ✅ PASSE — La base de code gère cela correctement. Cite le fichier et la ligne.
- ❌ ÉCHOUE — Une vulnérabilité existe. Documente-la complètement (voir format).
- ⚠️ PARTIEL — Couverture partielle, lacunes restantes. Explique ce qui manque.
- ⬚ N/A — Non applicable à cette base de code. Indique brièvement pourquoi.

**Ne saute aucun élément. Ne résume pas plusieurs éléments en un seul verdict.**

</methodology>

<output_format>

Pour chaque conclusion ❌ ÉCHOUE, utilise exactement cette structure :

CONCLUSION #[numéro]
- Sévérité : CRITIQUE / HAUTE / MOYENNE / BASSE
- Catégorie : ex. Secret exposé, Validation manquante, CORS trop ouvert, Injection SQL
- Emplacement : chemin/fichier.py:numéro_ligne
- CWE : CWE-XXX (Nom)

Ce qui ne va pas :
[Description en langage clair de la vulnérabilité]

Pourquoi c'est important :
[Ce qu'un attaquant pourrait réellement faire dans le contexte VINCI]

Le code vulnérable :
```python
[extrait de code exact]
```

La correction :
```python
[extrait de code corrigé, prêt à appliquer]
```

Effort : ~[X] minutes

</output_format>

<audit_checklist>

# Section 1 — Variables d'environnement et gestion des secrets

- 1.1 — Secrets codés en dur dans le code source : grep dans tous les fichiers `.py`, `.ts`, `.tsx`, `.js`, `.json`, `.yml`, `.env*` à la recherche des patterns suivants : `sk_live_`, `sk_test_`, `sk-` (Anthropic / OpenAI), `Bearer `, `eyJ` (préfixe JWT base64), `ghp_`, `gho_`, `github_pat_`, `xoxb-`, `xoxp-` (Slack), `AKIA` (AWS), toute chaîne alphanumérique de 32+ caractères entre guillemets dans le code source.

- 1.2 — Couverture du `.gitignore` : vérifie que `.env`, `.env.local`, `.env.production`, `*.env`, `**/secrets/`, `**/.pem`, `**/.key` sont tous dans le `.gitignore` racine et dans `backend/.gitignore` si présent. **Vérifie l'historique git** avec `git log --all --full-history -- .env` pour détecter tout `.env` qui aurait été committé puis supprimé (le secret reste exposé dans l'historique).

- 1.3 — Fuites de préfixe public : dans la stack Vite, le préfixe `VITE_` est intégré dans le bundle JS client. Vérifie qu'aucune des clés suivantes n'a le préfixe `VITE_` ou n'est lue côté client :
  - `ANTHROPIC_API_KEY` (clé API LLM)
  - `JWT_SECRET_KEY` (secret de signature JWT)
  - `DATABASE_URL` (chaîne de connexion DB)
  - Toute clé donnant un accès en écriture / admin

- 1.4 — Fuites dans la console / les erreurs : grep `console.log`, `console.error`, `print(`, `logger.info(`, `logger.error(`. Vérifie qu'aucune trace ne contient `os.environ`, `settings.JWT_SECRET_KEY`, `settings.ANTHROPIC_API_KEY`, ou un objet `User` complet (qui pourrait contenir un hash de password).

- 1.5 — Exposition des artefacts de build : vérifie `vite.config.ts`. La directive `build.sourcemap` doit être à `false` ou absente en production. Les source maps activées permettent à n'importe qui de reconstituer le code source côté front avec les noms de variables d'origine.

- 1.6 — Validation au démarrage : vérifie que `backend/app/core/config.py` lève une exception au démarrage si `JWT_SECRET_KEY` est absente ou vaut sa valeur par défaut « changeme ». Vérifie également que `DATABASE_URL` est obligatoire. L'application ne doit pas démarrer silencieusement avec des valeurs par défaut non sécurisées.

- 1.7 — Secret JWT robuste : vérifie que `JWT_SECRET_KEY` fait au minimum 32 caractères aléatoires (idéalement 64). Si la valeur par défaut est « changeme » ou « secret », c'est un échec critique.

# Section 2 — Sécurité de la base de données

(Section adaptée : nous utilisons PostgreSQL avec accès **uniquement côté serveur** via SQLAlchemy. Pas de RLS au sens Supabase, mais des contrôles d'accès dans le code.)

- 2.1 — Filtrage par user_id côté serveur : pour chaque endpoint qui retourne des données utilisateur (projets, vérifications, écarts, saisies chantier), vérifie que la requête SQL filtre **toujours** sur `user_id = current_user.id` (ou via un join sur les rôles), et que ce filtrage est fait **côté serveur**, pas côté client. Cherche les routes qui retournent toutes les lignes d'une table sans filtrage.

- 2.2 — Vérification d'autorisation par ressource : pour chaque endpoint qui prend un identifiant en paramètre (ex. `GET /api/projects/{id}`, `PATCH /api/gaps/{id}`), vérifie qu'avant de retourner ou modifier la ressource, le code vérifie que **l'utilisateur courant a bien accès à cette ressource**. Sinon un utilisateur authentifié peut lire/modifier les ressources des autres en devinant les IDs.

- 2.3 — Mass assignment : vérifie que les schémas Pydantic utilisés en entrée des `POST` et `PATCH` n'acceptent **pas** les champs sensibles (`id`, `user_id`, `created_at`, `is_admin`, `role`). Un attaquant qui POST un body avec `{"is_admin": true}` ne doit pas pouvoir s'élever en admin.

- 2.4 — Identité depuis la session, jamais depuis le body : vérifie que l'identité utilisateur pour les opérations d'écriture est dérivée de `Depends(get_current_user)`, jamais d'un champ `user_id` du body de requête.

- 2.5 — Injection SQL : grep les requêtes SQL brutes (`text(`, `execute(`, `.raw(`, f-strings dans des `text(...)`). SQLAlchemy ORM est sûr par défaut, mais les `text()` avec interpolation directe sont vulnérables. Vérifie que tous les paramètres dynamiques utilisent les bind params (`text("WHERE id = :id").bindparams(id=user_id)`).

- 2.6 — Migrations Alembic : vérifie que les migrations ne contiennent pas de DDL problématique (DROP TABLE en up, GRANT à un rôle public). Vérifie que les migrations sont versionnées dans le dépôt et que la dernière migration en base correspond à la dernière migration du dépôt.

- 2.7 — Hashage des mots de passe : vérifie que les mots de passe utilisateur sont hashés avec bcrypt (`passlib.context.CryptContext(schemes=["bcrypt"])`). Vérifie que le coût (rounds) est >= 12. Aucun stockage en clair, aucun hash MD5/SHA1.

- 2.8 — Permissions de la base : vérifie que la chaîne `DATABASE_URL` du backend pointe sur un utilisateur Postgres **non superuser**. En V1 Docker local c'est acceptable d'utiliser le compte par défaut, mais à documenter pour V2.

# Section 3 — Authentification et gestion des sessions

- 3.1 — Le middleware d'auth existe : vérifie que `Depends(get_current_user)` (ou équivalent) est présent sur **chaque** route protégée. Liste les routes du dossier `backend/app/api/routers/` et marque celles qui ne sont pas protégées.

- 3.2 — Routage par défaut en refus : vérifie le pattern. Soit toutes les routes sont protégées par défaut et les exceptions (login, register, healthcheck, fiche tableau publique) sont explicitement listées, soit chaque route est protégée individuellement. Le premier pattern est plus sûr car les nouvelles routes sont automatiquement protégées.

- 3.3 — Validation du JWT côté serveur : vérifie que la fonction `get_current_user` :
  - Décode le JWT avec `jose.jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])`
  - Vérifie l'expiration (claim `exp`)
  - Charge l'utilisateur depuis la base et lève `HTTPException(401)` si l'utilisateur est désactivé

- 3.4 — Gestionnaire de callback : la V1 n'utilise pas OAuth. Marquer N/A et noter qu'il faudra revérifier en V2 si Google SSO est ajouté.

- 3.5 — Stockage de session côté front : vérifie comment le JWT est stocké dans le navigateur. **Idéal** : cookie `httpOnly` + `Secure` + `SameSite=Strict`. **Acceptable en V1 Docker local** : `localStorage` (mais pas sessionStorage), avec mention claire dans le code que c'est V1 et qu'il faudra passer en cookie httpOnly avant tout déploiement réseau.

- 3.6 — Routes API protégées : pour **chaque** route API (lister exhaustivement), confirme qu'elle vérifie l'authentification avant traitement. Cherche en particulier les routes que Claude Code a pu ajouter dans les derniers modules (DOE, dashboard) où l'oubli est fréquent.

- 3.7 — OAuth : N/A en V1.

- 3.8 — Flux de réinitialisation de mot de passe : si implémenté, vérifie que les tokens de reset expirent (< 1h), sont à usage unique, et sont transmis par e-mail uniquement (jamais dans une URL côté client). Si non implémenté, N/A.

- 3.9 — Route publique fiche tableau (`GET /t/{token}`) : c'est la **seule route publique non authentifiée** du projet. Vérifie que :
  - Le token est aléatoire long (>= 24 caractères, généré par `secrets.token_urlsafe()`)
  - Le token ne contient ni l'ID du projet, ni l'ID du tableau (sinon devinable)
  - La route ne retourne **que** les informations strictement nécessaires à l'affichage de la fiche, pas les données complètes du projet ou du client
  - Aucune action de modification n'est possible via ce token (lecture seule)

# Section 4 — Validation côté serveur

- 4.1 — Validation par schéma Pydantic : vérifie que toutes les routes API reçoivent leurs entrées via des modèles Pydantic, jamais via `Request.json()` brut. Chaque champ doit avoir un type déclaré et, si pertinent, des contraintes (`Field(min_length=, max_length=, ge=, le=, regex=)`).

- 4.2 — Identité depuis la session : déjà couvert en 2.4. Confirmer.

- 4.3 — Nettoyage des entrées rendues en HTML : grep `dangerouslySetInnerHTML` côté React. Aucune occurrence ne devrait contenir du contenu utilisateur non échappé. Si le DOE PDF rend du contenu utilisateur (commentaires de Chef de Chantier), vérifier que ReportLab échappe correctement.

- 4.4 — Méthodes HTTP appropriées : vérifie que les opérations qui modifient l'état utilisent `POST` / `PUT` / `PATCH` / `DELETE`, jamais `GET`. Liste les routes qui ne respectent pas ce principe.

- 4.5 — Fuites d'informations dans les erreurs : vérifie que la production n'expose pas les traces de pile. Le handler d'exception global dans FastAPI doit retourner un message générique en prod (`"Internal server error"`) et logger le détail côté serveur. En dev, c'est OK d'exposer les traces.

- 4.6 — Vérification de signature de webhook : N/A en V1 (pas de webhook).

- 4.7 — Validation des fichiers uploadés (CRITIQUE pour ce projet) : vérifie pour les uploads CANECO Excel, bordereau Excel, CPS PDF :
  - **Type MIME vérifié** côté serveur (pas juste l'extension du nom de fichier)
  - **Taille maximale** appliquée (par exemple 50 Mo pour les Excel, 100 Mo pour les PDF)
  - **Pas d'évaluation de contenu actif** : les Excel ne doivent pas exécuter de macros (utiliser `openpyxl` qui ne charge pas les macros par défaut, jamais `xlwings`)
  - **Stockage dans un dossier non exécutable** (pas dans la racine web statique)

- 4.8 — XML External Entities (XXE) : si le projet parse du XML (peu probable mais à vérifier), s'assurer que les parseurs sont configurés sans résolution d'entités externes. Pour `lxml` : `etree.parse(path, parser=etree.XMLParser(resolve_entities=False))`.

# Section 5 — Sécurité des dépendances et packages

- 5.1 — Audit Python : lance `cd backend && pip-audit` (ou `safety check` si `pip-audit` n'est pas dispo). Rapporte toutes les vulnérabilités groupées par sévérité.

- 5.2 — Audit Node : lance `cd frontend && npm audit` (ou `pnpm audit`). Idem.

- 5.3 — Packages hallucinés : vérifie que tous les packages dans `backend/pyproject.toml` et `frontend/package.json` existent réellement sur PyPI / npm avec un nombre de téléchargements significatif (> 10 000). Les outils IA hallucinent parfois des noms, et des attaquants publient ensuite des malwares sous ces noms. Liste tout package avec moins de 1000 téléchargements/mois ou publié dans les 30 derniers jours.

- 5.4 — Lockfiles committés : vérifie que `backend/poetry.lock` (ou `requirements.lock`) et `frontend/pnpm-lock.yaml` (ou `package-lock.json`) sont bien dans le dépôt.

- 5.5 — Packages obsolètes : vérifie spécialement les versions de :
  - `fastapi` (CVE possibles dans les vieilles versions)
  - `python-jose` (CVE-2024-33663 sur les vieilles versions, vérifier >= 3.3.0)
  - `passlib` ou `bcrypt`
  - `react`, `vite`

- 5.6 — Dépendances inutilisées : vérifie qu'il n'y a pas de packages dans `pyproject.toml` ou `package.json` qui ne sont importés nulle part dans le code. Chaque package inutilisé est une surface d'attaque.

# Section 6 — Limitation de débit (rate limiting)

- 6.1 — Endpoints d'authentification : vérifie que `POST /api/auth/login` et `POST /api/auth/register` (si encore actif) ont une limitation de débit pour prévenir le bourrage d'identifiants. En V1 acceptable d'utiliser `slowapi` (extension FastAPI) avec un compteur en mémoire. À documenter pour passer sur Redis en V2.

- 6.2 — Endpoints LLM : si la couche LLM Anthropic est appelée, vérifie que l'endpoint qui la déclenche a une limitation de débit stricte. Sans elle, un attaquant authentifié pourrait spammer l'endpoint et faire exploser la facture API Anthropic.

- 6.3 — Endpoints d'upload de fichiers : vérifie qu'un utilisateur ne peut pas uploader 1000 fichiers à la suite (DoS du stockage local).

# Section 7 — Configuration CORS

- 7.1 — CORS du backend : vérifie dans `backend/app/main.py` que `CORSMiddleware` est configuré avec une liste explicite d'origines (`allow_origins=["http://localhost:5173"]` en dev, `["https://app-pilote.actemium.fr"]` en prod), **jamais** avec `["*"]`.

- 7.2 — Mode credentials : vérifie que `allow_credentials=True` n'est associé qu'à des origines spécifiques, jamais à `"*"` (et FastAPI rejette d'ailleurs cette combinaison).

- 7.3 — En-têtes autorisés : vérifie que `allow_headers` est limité aux en-têtes nécessaires (`Authorization`, `Content-Type`), pas `["*"]`.

# Section 8 — Sécurité des téléchargements de fichiers

(Critique pour ce projet : on traite des fichiers Excel et PDF clients VINCI.)

- 8.1 — Validation côté serveur : déjà couvert en 4.7. Confirmer en regardant le code des routers `caneco-imports`, `bordereau-imports`, `cps-imports`.

- 8.2 — Permissions de stockage : vérifie où sont stockés les fichiers uploadés.
  - **Idéal V1** : stockage dans `data/uploads/<project_id>/` avec lecture restreinte au backend uniquement
  - **Échec** : stockage dans `frontend/public/` ou tout dossier servi statiquement

- 8.3 — Prévention d'exécution : vérifie que le dossier d'uploads n'est pas dans le path exécutable d'un serveur web. Sur Docker, le backend ne sert que des routes FastAPI, pas de fichiers statiques arbitraires.

- 8.4 — Génération PDF (DOE, fiches QR) : vérifie que `ReportLab` est utilisé sans interpolation directe de contenu utilisateur dans des éléments scriptables. ReportLab est sûr par défaut, mais à confirmer.

- 8.5 — Étiquettes QR : vérifie que les payloads QR ne contiennent **aucune donnée sensible**. Le payload doit être uniquement une URL de la forme `https://<domain>/t/<token_aléatoire>`. Aucun JWT, aucun nom de client, aucune donnée projet directement encodée dans le QR.

# Section 9 — Spécifique au projet CANECO BT

- 9.1 — Logs de requêtes : vérifie que les logs serveur ne contiennent pas le contenu intégral des fichiers uploadés (CPS, bordereau) ni les saisies chantier. Logger uniquement les métadonnées (nom du fichier, taille, user_id, project_id, timestamp).

- 9.2 — Données dans les rapports d'écarts : vérifie que les rapports d'écarts (et leur export PDF/Excel) ne contiennent que les données du projet courant, pas de mélange avec d'autres projets.

- 9.3 — Photos de chantier : vérifie que les photos uploadées par les Chefs de Chantier sont stockées de manière sécurisée et ne sont accessibles qu'aux utilisateurs ayant accès au projet correspondant.

- 9.4 — Tokens des fiches tableau publiques : voir 3.9. Ces tokens donnent accès en lecture sans authentification. Vérifier qu'on ne peut pas, depuis un token de fiche tableau, accéder à d'autres tableaux ou à d'autres projets via des URLs voisines.

- 9.5 — Backups et export DOE : si une fonctionnalité d'export complet du projet existe, vérifier que seul le RA du projet ou un admin peut la déclencher.

- 9.6 — Données client dans les seeds : vérifie que `data/seed/dachser/` n'est pas committé dans le dépôt si le dépôt est public. Si privé (recommandé), c'est OK.

</audit_checklist>

<final_report>

Après avoir complété tous les éléments de la checklist, livre cette structure finale :

# 1. Évaluation de la posture de sécurité

🔴 CRITIQUE — Exposition active de données ou contournement d'authentification. Arrêter tout déploiement.
🟠 À AMÉLIORER — Lacunes significatives qui seraient exploitables.
🟡 ACCEPTABLE — Problèmes mineurs, pas de risque immédiat d'exposition de données.
🟢 SOLIDE — Bien sécurisé avec uniquement des conclusions informationnelles.

Rédige un paragraphe de résumé exécutif (10 lignes max) qui justifie le niveau retenu, en gardant en tête le contexte : V1 pilote sur poste développeur, données projet VINCI sensibles.

# 2. Conclusions critiques et hautes

Liste toutes les conclusions de sévérité CRITIQUE et HAUTE. Ces éléments sont à corriger **avant** le tag `v0.1.0`.

# 3. Victoires rapides

Liste les corrections qui prennent moins de 10 minutes chacune mais améliorent significativement la posture de sécurité.

# 4. Plan de remédiation priorisé

Une liste numérotée de **toutes** les conclusions, ordonnées par :
1. Sévérité (critique avant haute avant moyenne avant basse)
2. Effort (corrections rapides avant refactorisations complexes dans chaque niveau)

Pour chaque élément, indique le temps de correction estimé.

# 5. Ce qui est déjà bien fait

Liste les bonnes pratiques correctement implémentées. C'est important pour ne pas casser ces patterns dans les évolutions futures.

# 6. Résumé de la checklist

Produis un résumé compact verdict par verdict :

```
1.1 ✅  1.2 ✅  1.3 ❌  1.4 ✅  1.5 ⚠️  1.6 ✅  1.7 ✅
2.1 ✅  2.2 ❌  2.3 ✅  2.4 ✅  2.5 ✅  2.6 ✅  2.7 ✅  2.8 ⬚
3.1 ✅  3.2 ⚠️  3.3 ✅  3.4 ⬚  3.5 ⚠️  3.6 ✅  3.7 ⬚  3.8 ⬚  3.9 ✅
4.1 ✅  4.2 ✅  4.3 ✅  4.4 ✅  4.5 ⚠️  4.6 ⬚  4.7 ✅  4.8 ⬚
5.1 ✅  5.2 ✅  5.3 ✅  5.4 ✅  5.5 ✅  5.6 ⚠️
6.1 ❌  6.2 ❌  6.3 ⚠️
7.1 ✅  7.2 ✅  7.3 ✅
8.1 ✅  8.2 ✅  8.3 ✅  8.4 ✅  8.5 ✅
9.1 ⚠️  9.2 ✅  9.3 ✅  9.4 ✅  9.5 ✅  9.6 ✅
```

</final_report>

<instructions_finales>

Lis l'intégralité de la base de code avant de produire des conclusions. Comprends d'abord l'architecture. Puis parcours chaque élément de la checklist un par un.

Sois minutieux mais pratique. Priorise les vulnérabilités réelles et exploitables sur les préoccupations théoriques. Garde en tête le contexte : V1 pilote, déploiement Docker local d'abord, données projet VINCI sensibles, code en partie généré par un assistant IA.

Ne regroupe pas plusieurs éléments de la checklist dans une seule réponse. Chaque élément reçoit son propre verdict explicite.

Si tu es incertain sur une conclusion, signale-la comme ⚠️ PARTIEL et explique ce que tu aurais besoin de vérifier de plus.

Une fois l'audit livré, **propose un plan de correction des conclusions CRITIQUES et HAUTES**, et **applique ces corrections** après ma validation. Pour les conclusions MOYENNES et BASSES, génère uniquement les correctifs en suggestion (commit séparé que je validerai à part).

Commence par la passe de découverte. Quand tu as construit ton modèle mental de l'architecture, présente-le-moi en 10 lignes avant de démarrer la passe d'audit.

===== FIN PROMPT =====
```

---

## Comment exploiter le rapport d'audit

### 1. Faire l'audit avant le tag v0.1.0

Une fois que Claude Code a terminé le Module 6 du `PROMPT_CLAUDE_CODE.md`, ne crée **pas** tout de suite le tag `v0.1.0`. À la place :

1. Crée une branche `audit/security-v1` : `git checkout -b audit/security-v1`
2. Lance Claude Code dans cette branche
3. Colle le prompt ci-dessus (entre les balises `===== DÉBUT PROMPT =====` et `===== FIN PROMPT =====`)
4. Laisse Claude Code dérouler l'audit (15 à 30 minutes)
5. Lis le rapport. **Aucune conclusion CRITIQUE ne doit rester** avant le tag v0.1.0.
6. Demande à Claude Code de corriger toutes les conclusions critiques et hautes
7. Vérifie que les tests passent toujours (`pytest`, `pnpm test`)
8. Merge la branche dans `main` avec un commit `security: corrections de l'audit V1`
9. Crée le tag `v0.1.0`

### 2. Faire l'audit avant chaque release majeure

Refais l'audit avant chaque tag (`v0.2.0`, `v0.3.0`, etc.). Les vulnérabilités introduites entre deux versions sont fréquentes — surtout sur les nouveaux modules.

### 3. Sauvegarde des rapports d'audit

Sauvegarde chaque rapport dans `docs/security_audits/YYYY-MM-DD_audit.md`. Cela donne une traçabilité utile pour ton encadrant et pour montrer la maturité du projet face au jury VEAO.

### 4. Adapter le prompt pour la V2

En V2 (déploiement réseau), plusieurs sections deviennent plus strictes :
- 3.5 (cookies httpOnly obligatoires, plus de localStorage)
- 6.1, 6.2, 6.3 (rate limiting Redis obligatoire)
- 7.1 (CORS production stricte)
- 9.6 (data/seed/dachser/ ne doit jamais aller en V2 hosting public)

Il faudra alors actualiser ce fichier `SECURITY_AUDIT_PROMPT.md` en ajustant ces sections.

---

## Recommandation pour le pitch face au jury

L'audit de sécurité est un **point fort** du dossier face au jury VEAO. Il prouve que :
1. Le projet n'est pas qu'une preuve de concept jetable
2. Tu as anticipé les enjeux de production
3. Tu maîtrises la gouvernance d'un projet d'IA appliquée

Si on te demande pendant le pitch « Comment garantissez-vous que l'outil ne fuit pas les données projet ? », ta réponse :

> « Nous avons appliqué un audit de sécurité systématique sur 9 sections critiques avant chaque release. Le rapport d'audit est versionné dans le dépôt et signé pour chaque tag. Pour la V1 pilote, nous sommes au niveau ACCEPTABLE avec un plan de durcissement précis pour la V2 (cookies httpOnly, rate limiting Redis, hébergement contrôlé). »

Cette réponse impressionne plus qu'une démo technique.

---

**Fin du SECURITY_AUDIT_PROMPT.md**
