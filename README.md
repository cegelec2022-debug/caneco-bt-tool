# Valorisation des données CANECO BT

Outil de gestion et de valorisation des données issues de CANECO BT, développé dans le cadre du Challenge Innovation VEAO 2026 (Actemium Cegelec Tanger, VINCI Energies). De la note de calcul CANECO BT au DOE livré au client, chaque mètre de câble est tracé, vérifié et croisé avec les autres sources de vérité du projet (CPS, bordereau, norme NF C 15-100).

L'outil s'organise en trois briques connectées autour d'une base de données unique :

1. **Vérification CANECO** : rapprochement automatique note CANECO / bordereau / CPS, référentiel d'écarts E-001 à E-010, vérification normative NF C 15-100.
2. **Tableau de bord multi-projets et saisie chantier** : pilotage RA en temps réel, saisie mobile des longueurs tirées par le Chef de Chantier.
3. **Carnet de câbles, QR codes et DOE** : fiche publique par tableau accessible par scan, planches d'étiquettes A4, stock câbles, génération du DOE.

Cas pilote : projet DACHSER, Lot 3 Électricité. Second projet de validation : NSK.

---

## 1. Accès au code source

Le dépôt est hébergé sur GitHub (privé) : `https://github.com/alysquart/caneco-bt-tool`

Règle de reprise : le dépôt d'origine (`alysquart/caneco-bt-tool`) est figé comme référence. Toute reprise se fait sur un **fork**, c'est-à-dire votre propre copie du dépôt sur votre compte GitHub : vos modifications restent chez vous et ne touchent jamais le dépôt d'origine.

Procédure :

1. Créer un compte GitHub si nécessaire : https://github.com/signup
2. Transmettre votre nom d'utilisateur GitHub au propriétaire du dépôt (alysquart), qui vous ajoutera comme collaborateur en lecture (nécessaire pour voir un dépôt privé et pouvoir le forker).
3. Une fois l'invitation acceptée, **forker** le dépôt : ouvrir https://github.com/alysquart/caneco-bt-tool, bouton **Fork** en haut à droite, garder le nom `caneco-bt-tool`. La copie est créée sur votre compte.
4. Cloner **votre fork** (et non le dépôt d'origine) :
   ```bash
   git clone https://github.com/<votre-compte>/caneco-bt-tool.git
   ```
5. Vérifier que le dépôt distant pointe bien vers votre compte : `git remote -v` doit afficher `<votre-compte>/caneco-bt-tool`, pas `alysquart/caneco-bt-tool`.

Tous vos commits et push iront alors sur votre fork uniquement. Ne poussez jamais vers `alysquart/caneco-bt-tool`. La branche `main` du fork contient la dernière version stable au moment de la reprise.

---

## 2. Logiciels à installer

Installer dans cet ordre. Tous les liens pointent vers les pages officielles de téléchargement.

| Logiciel | Version | Rôle | Lien de téléchargement |
|---|---|---|---|
| Git | dernière | Gestion de versions, clonage du dépôt | https://git-scm.com/downloads |
| Docker Desktop | dernière | Exécute PostgreSQL, le backend et le frontend sans installation manuelle | https://www.docker.com/products/docker-desktop/ |
| Visual Studio Code | dernière | Éditeur de code | https://code.visualstudio.com/ |
| Node.js | 20 LTS | Frontend React (utile hors Docker et pour Claude Code) | https://nodejs.org/ |
| Python | 3.11 | Backend FastAPI (utile hors Docker) | https://www.python.org/downloads/ |
| GitHub CLI (optionnel) | dernière | Opérations GitHub depuis le terminal | https://cli.github.com/ |
| Claude Code (optionnel, recommandé) | dernière | Assistant de développement IA utilisé pour construire ce projet | https://claude.com/claude-code |
| ngrok (optionnel) | dernière | Lien public permanent pour les QR codes et les démonstrations (voir section 3.6) | https://ngrok.com/download |

Notes d'installation :

- **Docker Desktop** : sous Windows, activer WSL 2 si l'installeur le demande. Après installation, lancer Docker Desktop et vérifier que l'icône indique "Engine running".
- **Python** : cocher "Add Python to PATH" pendant l'installation.
- **Node.js** : choisir la version LTS (20.x). Vérifier avec `node --version`.
- Docker seul suffit pour lancer l'application. Node et Python ne sont nécessaires que pour travailler hors conteneurs (débogage fin, exécution locale des tests).

---

## 3. Installation du projet

### 3.1 Cloner et configurer

```bash
# 1. Cloner le dépôt (après avoir reçu l'accès)
git clone https://github.com/alysquart/caneco-bt-tool.git
cd caneco-bt-tool

# 2. Créer les fichiers de variables d'environnement à partir des modèles
# Windows (PowerShell) :
copy .env.example .env
copy backend\.env.example backend\.env
# macOS / Linux :
cp .env.example .env
cp backend/.env.example backend/.env
```

Les valeurs par défaut des `.env.example` fonctionnent en développement local. La clé `ANTHROPIC_API_KEY` est optionnelle : sans elle, l'outil fonctionne en mode 100 % déterministe (aucune fonction critique ne dépend du LLM).

### 3.2 Démarrer l'application

```bash
# Démarrer les trois services (PostgreSQL + backend + frontend)
docker compose up -d

# Vérifier que les trois conteneurs sont "running"
docker compose ps
```

Au premier démarrage, le backend applique automatiquement les migrations de base de données (Alembic) et crée les comptes de démonstration ainsi que le projet pilote DACHSER-L3.

### 3.3 Vérifier que tout fonctionne

| Service | URL | Résultat attendu |
|---|---|---|
| Frontend | http://localhost:5173 | Page de connexion |
| API (Swagger) | http://localhost:8000/api/docs | Documentation interactive de l'API |
| Healthcheck | http://localhost:8000/api/health | `{"status":"ok"}` |

### 3.4 Comptes de démonstration

| Rôle | E-mail | Mot de passe |
|---|---|---|
| Administrateur | admin@actemium.fr | Demo2026! |
| Responsable d'Études (BE) | be@actemium.fr | Demo2026! |
| Chef de Chantier | chef@actemium.fr | Demo2026! |
| Responsable d'Affaires (RA) | ra@actemium.fr | Demo2026! |

### 3.5 Charger les données du cas pilote

Se connecter avec le compte BE, ouvrir le projet DACHSER-L3, onglet Études, puis uploader le fichier `data/seed/dachser/DATA_DACHSER_INDICE_B.XLS`. Les autres pièces du projet (bordereau, CPS) se chargent depuis leurs onglets respectifs.

### 3.6 Lien public permanent avec ngrok (QR codes et démonstrations)

En local, l'application n'est visible que sur le poste de développement. Un tunnel ngrok expose le frontend sur une URL publique stable, indispensable pour deux usages :

- les QR codes collés sur les armoires doivent s'ouvrir depuis n'importe quel téléphone (la variable `PUBLIC_BASE_URL` de `docker-compose.yml` est encodée dans chaque QR généré) ;
- les démonstrations à distance (encadrant, jury, agence) sans rien installer chez l'interlocuteur.

C'est le montage actuellement en service sur le projet, avec une URL qui ne change jamais.

**Préparation du compte (commune aux deux méthodes)**

1. Créer un compte ngrok gratuit : https://dashboard.ngrok.com/signup
2. Récupérer l'authtoken : https://dashboard.ngrok.com/get-started/your-authtoken
3. Réserver le domaine statique gratuit du compte : https://dashboard.ngrok.com/domains (bouton New Domain). Le plan gratuit inclut un domaine fixe du type `xxxx-yyyy-zzzz.ngrok-free.dev` : c'est lui qui rend le lien permanent.

L'authtoken est un secret : ne jamais l'écrire dans un fichier du dépôt ni le committer.

**Méthode 1 : mise en place manuelle**

```bash
# 1. Installer ngrok (téléchargement : https://ngrok.com/download), puis enregistrer le token
ngrok config add-authtoken <VOTRE_AUTHTOKEN>

# 2. Ouvrir le tunnel vers le frontend avec le domaine réservé
ngrok http 5173 --domain=<votre-domaine>.ngrok-free.dev
```

3. Mettre à jour `PUBLIC_BASE_URL` dans `docker-compose.yml` avec `https://<votre-domaine>.ngrok-free.dev`, puis recréer le backend : `docker compose up -d backend`.
4. Régénérer les tableaux (onglet Tableaux, bouton de génération) pour que les QR codes encodent la nouvelle URL. La régénération conserve les tokens existants : les étiquettes déjà imprimées restent valides.
5. Pour que le tunnel démarre tout seul à chaque ouverture de session Windows : touche Windows + R, taper `shell:startup`, puis déposer dans ce dossier un script `.cmd` contenant la commande du point 2 (idéalement dans une boucle de relance en cas de coupure) :

```
:boucle
ngrok http 5173 --domain=<votre-domaine>.ngrok-free.dev
timeout /t 20
goto boucle
```

Cas particulier réseau d'entreprise : si le téléchargement du binaire ngrok est bloqué (situation rencontrée à l'agence, où seul le port 443 sort), passer par le SDK Node : `npm install @ngrok/ngrok`, puis un petit script `launch.js` qui ouvre le tunnel vers le port 5173 et lit le token depuis la variable d'environnement `NGROK_AUTHTOKEN`. C'est le montage actuellement en place, avec relance automatique et lancement invisible au démarrage de session.

**Méthode 2 : mise en place par Claude Code**

Ouvrir Claude Code dans le dossier du projet et lui demander, par exemple :

```
Mets en place un tunnel ngrok permanent vers le port 5173.
Mon domaine statique reserve : <votre-domaine>.ngrok-free.dev
Mon authtoken est dans la variable d'environnement NGROK_AUTHTOKEN (ne l'ecris jamais en dur ni dans le depot).
Je veux : demarrage automatique a l'ouverture de session Windows, relance automatique en cas de coupure,
mise a jour de PUBLIC_BASE_URL dans docker-compose.yml, et la procedure pour regenerer les QR codes.
Si le telechargement du binaire ngrok est bloque par le reseau, utilise le SDK Node @ngrok/ngrok.
```

Claude Code crée les scripts, configure le démarrage automatique, met à jour la configuration et vérifie que le lien répond. Définir d'abord le token en variable d'environnement utilisateur : `setx NGROK_AUTHTOKEN "<VOTRE_AUTHTOKEN>"` (puis rouvrir le terminal).

**Limites du plan gratuit à connaître**

- Une seule session de tunnel à la fois : si une erreur ERR_NGROK_108 ou ERR_NGROK_334 (« endpoint already online ») apparaît, fermer toutes les instances ngrok/node en double, attendre environ 40 secondes, puis relancer une seule instance.
- Au premier accès depuis un navigateur, ngrok affiche une page intermédiaire « Visit Site » : prévenir l'interlocuteur, il suffit de cliquer une fois.
- Pour une démonstration fluide à distance, servir le build de production du frontend : `docker compose -f docker-compose.yml -f docker-compose.preview.yml up -d frontend` (détail dans la documentation technique, section 7.2).

---

## 4. Lancer les tests

```bash
# Tests backend (pytest), depuis les conteneurs :
docker compose exec backend pytest

# Ou en local (nécessite Python 3.11 + pip install -r backend/requirements-dev.txt) :
cd backend && pytest

# Tests backend avec couverture
cd backend && pytest --cov=app --cov-report=term-missing

# Tests frontend (Vitest), nécessite Node 20 :
cd frontend && npm install && npm test
```

---

## 5. Commandes Docker utiles

```bash
docker compose up -d              # Démarrer en arrière-plan
docker compose logs -f            # Logs en temps réel (tous services)
docker compose logs -f backend    # Logs du backend uniquement
docker compose restart backend    # Redémarrer le backend
docker compose restart frontend   # Redémarrer le frontend (après modif vite.config.ts)
docker compose down               # Arrêter les services
docker compose down -v            # Arrêter ET supprimer la base de données
```

Réinitialiser complètement la base (perte de toutes les données saisies) :

```bash
docker compose down -v
docker compose up -d
```

---

## 6. Travailler avec Claude Code

Ce projet a été développé avec Claude Code, l'assistant de développement en ligne de commande d'Anthropic. Le fichier `CLAUDE.md` à la racine contient le contexte projet, les conventions de code et les garde-fous de sécurité : Claude Code le lit automatiquement à chaque session, ce qui lui donne immédiatement le contexte complet.

### 6.1 Installation

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

Nécessite un abonnement Claude (Pro ou supérieur) ou une clé API Anthropic. Au premier lancement de `claude`, une page de navigateur s'ouvre pour l'authentification.

### 6.2 Utilisation sur ce projet

```bash
cd caneco-bt-tool
claude
```

Exemples de demandes utiles pour la prise en main :

- "Explique-moi l'architecture du backend, dossier par dossier."
- "Montre-moi comment le moteur de vérification détecte l'écart E-004."
- "Lance les tests backend et explique les éventuels échecs."

### 6.3 Lier Claude Code à votre GitHub (optionnel)

Installer GitHub CLI puis s'authentifier :

```bash
gh auth login
# Choisir : GitHub.com > HTTPS > Yes (authentifier git) > Login with a web browser
```

Claude Code peut alors créer des branches, committer, pousser et ouvrir des pull requests via `gh` sur demande.

### 6.4 Règles du projet à respecter

Le fichier `CLAUDE.md` impose notamment :

- Aucun secret en dur dans le code (tout passe par variables d'environnement).
- Ne jamais committer les fichiers `.env`.
- Ne jamais modifier ou supprimer les fichiers de référence dans `data/seed/`.
- Messages de commit au format Conventional Commits (`feat:`, `fix:`, `docs:`, ...).
- Branche `main` stable ; travailler sur des branches `feat/...` ou `fix/...`.
- Pas d'emoji dans le code, les commits ni l'interface.

---

## 7. Structure du projet

```
caneco-bt-tool/
├── backend/                Python 3.11 + FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/routers/    Endpoints REST (auth, projects, caneco, verification, ...)
│   │   ├── core/           Configuration, sécurité JWT, logging, rate limiting
│   │   ├── db/             Session, migrations, seed (comptes démo + projet pilote)
│   │   ├── models/         Modèles SQLAlchemy
│   │   ├── schemas/        Schémas Pydantic (DTO API)
│   │   ├── services/       Logique métier (parsers, vérification, carnet, stock, QR, DOE)
│   │   └── repositories/   Accès base de données
│   └── tests/              Tests pytest (238+)
├── frontend/               React 18 + TypeScript + Vite + Tailwind + shadcn/ui
│   └── src/
│       ├── pages/          Login, Projets, Projet (onglets), Dashboard, Fiche publique QR
│       ├── components/     Layout, route protégée, composants UI
│       └── api/            Client API (axios + TanStack Query)
├── data/seed/dachser/      Fichiers de référence DACHSER (ne pas modifier)
├── docs/                   PRD, prompts de développement, audits de sécurité
├── docker-compose.yml      PostgreSQL 16 + backend + frontend (développement)
├── docker-compose.preview.yml  Mode démonstration (build de production du frontend)
├── CLAUDE.md               Contexte et conventions pour Claude Code
├── PRD.md                  Vision produit et périmètre fonctionnel
└── CHANGELOG.md            Historique des fonctionnalités livrées
```

---

## 8. Documents de référence

- `PRD.md` : vision produit, personas, périmètre V1, roadmap
- `CLAUDE.md` : conventions de code, garde-fous de sécurité, workflow
- `CHANGELOG.md` : historique détaillé des modules livrés
- `docs/PROMPT_CLAUDE_CODE.md` : plan de développement initial
- `docs/SECURITY_AUDIT_PROMPT.md` : procédure d'audit de sécurité avant chaque tag de version
- `docs/DOCUMENTATION_TECHNIQUE.md` : documentation technique complète (architecture, API, modèles de données, services)
- `docs/PROMPT_REPRENEUR.md` : installation automatisée de bout en bout pilotée par Claude Code (pour un repreneur non technique : donner ce fichier à Claude Code, qui s'occupe de tout, de l'accès GitHub jusqu'au tunnel ngrok permanent)

---

## 9. Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| `Cannot connect to Docker daemon` | Docker Desktop non lancé | Lancer Docker Desktop, attendre "Engine running", relancer la commande |
| Port 8000 ou 5173 déjà occupé | Autre application sur le port | Modifier le mapping de ports dans `docker-compose.yml` (ex. `8001:8000`) |
| Page blanche sur http://localhost:5173 | Frontend pas encore démarré | Attendre 30 s au premier lancement (installation des dépendances), puis `docker compose logs -f frontend` |
| Erreur 401 sur toutes les requêtes | Session expirée | Se reconnecter (le token JWT expire après 60 minutes) |
| Le hot reload ne fonctionne plus | Watcher Vite bloqué | `docker compose restart frontend` |
| La base semble corrompue ou incohérente | Migrations partielles | `docker compose down -v` puis `docker compose up -d` (repart de zéro) |
| Les QR codes scannés ne s'ouvrent pas depuis un téléphone | `PUBLIC_BASE_URL` pointe vers une URL non accessible | Mettre en place le tunnel ngrok (section 3.6), mettre à jour `docker-compose.yml`, puis régénérer les tableaux |
| Erreur ngrok ERR_NGROK_108 ou 334 | Plusieurs tunnels lancés en même temps (limite du plan gratuit) | Fermer toutes les instances ngrok/node, attendre 40 s, relancer une seule instance |
