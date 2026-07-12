# Prise en main automatisée du projet CANECO BT — fichier à donner à Claude Code

## Partie 1 — Notice pour le repreneur (à lire, 2 minutes)

Ce fichier permet d'installer et de mettre en service le projet « Valorisation des données CANECO BT » sans compétence technique particulière. C'est Claude Code, l'assistant de développement d'Anthropic, qui fait le travail : il vous posera des questions simples une par une, vous dira où obtenir chaque accès, et s'occupera de tout le reste (téléchargement du code, configuration, lancement, lien public permanent).

Avant de commencer, il vous faut seulement :

1. **Visual Studio Code** installé : https://code.visualstudio.com/
2. **Node.js version LTS** installé (nécessaire pour Claude Code) : https://nodejs.org/
3. **Claude Code** installé. Ouvrir un terminal (dans VS Code : menu Terminal, Nouveau terminal) et taper :
   ```
   npm install -g @anthropic-ai/claude-code
   ```
4. Un **abonnement Claude** (Pro ou supérieur) : https://claude.com/ — au premier lancement de Claude Code, une page s'ouvrira dans le navigateur pour vous connecter.

Ensuite :

5. Enregistrer ce fichier dans un dossier de travail, par exemple `Documents\projets\`.
6. Dans le terminal, se placer dans ce dossier puis lancer Claude Code :
   ```
   cd Documents\projets
   claude
   ```
7. Taper exactement cette phrase et appuyer sur Entrée :

   > Lis le fichier PROMPT_REPRENEUR.md qui se trouve dans ce dossier et exécute la mission qu'il contient, étape par étape.

C'est tout. Claude Code prend la main, vous guide et vous demande ce qu'il lui faut au bon moment. Répondez à ses questions ; quand il demande une autorisation pour exécuter une commande, validez si cela correspond à ce qu'il vient d'expliquer.

---

## Partie 2 — Mission pour Claude Code

Tu es Claude Code. La personne en face de toi reprend le projet « Valorisation des données CANECO BT » (dépôt `caneco-bt-tool`, Actemium Cegelec Tanger, VINCI Energies) après le départ du développeur initial, Aly Aly SANOH. Elle n'est pas nécessairement technique. Ta mission : l'amener d'un ordinateur vide à une installation complète et en service, identique à celle du développeur initial.

### Règles de conduite

1. Travaille strictement étape par étape, dans l'ordre ci-dessous. Ne passe à l'étape suivante qu'après avoir vérifié que l'étape courante fonctionne.
2. Pose une seule question à la fois, en français simple, sans jargon. Quand l'utilisateur doit obtenir un accès ou créer un compte, donne-lui le lien exact, explique quoi cliquer, et attends qu'il te donne le résultat.
3. Ne stocke jamais un secret (token ngrok, mot de passe, clé API) dans un fichier du dépôt ni dans un commit. Les secrets passent par variables d'environnement ou fichiers `.env` non versionnés.
4. Une fois le dépôt cloné, lis son fichier `CLAUDE.md` et respecte toutes ses conventions et garde-fous pour la suite.
5. À chaque étape terminée, annonce clairement : ce qui a été fait, comment tu l'as vérifié, et ce qui vient ensuite.
6. Si quelque chose échoue, diagnostique et corrige toi-même ; ne demande à l'utilisateur que ce que lui seul peut faire (créer un compte, cliquer sur une invitation, donner un token).

### Étape 1 — Vérifier les outils installés

Vérifie la présence de : `git`, `docker` (et que Docker Desktop est démarré), `node`, `gh` (GitHub CLI, optionnel). Pour chaque outil manquant, donne le lien officiel de téléchargement, explique l'installation en deux phrases, puis attends que l'utilisateur confirme pour revérifier :

- Git : https://git-scm.com/downloads
- Docker Desktop : https://www.docker.com/products/docker-desktop/ (sous Windows, accepter l'activation de WSL 2 si proposée ; après installation, le lancer et attendre « Engine running »)
- Node.js LTS : https://nodejs.org/
- GitHub CLI : https://cli.github.com/

Docker est indispensable. Ne continue pas tant que `docker info` ne répond pas correctement.

### Étape 2 — Accès GitHub et récupération du code

1. Demande à l'utilisateur s'il a un compte GitHub. Sinon, fais-le créer : https://github.com/signup
2. Le dépôt source est privé : `https://github.com/alysquart/caneco-bt-tool`. Demande à l'utilisateur son nom d'utilisateur GitHub et dis-lui de l'envoyer à Aly Aly SANOH pour être ajouté comme collaborateur (le propriétaire fait : Settings, Collaborators, Add people). Attends qu'il ait accepté l'invitation reçue par e-mail.
3. Authentifie git sur sa machine : si `gh` est installé, utilise `gh auth login` (GitHub.com, HTTPS, authentifier git, connexion par navigateur). Sinon, le clone HTTPS demandera ses identifiants (un Personal Access Token peut être créé sur https://github.com/settings/tokens si nécessaire ; guide-le).
4. **Règle imposée : travailler sur un fork, jamais sur le dépôt d'origine.** Le dépôt `alysquart/caneco-bt-tool` est la référence figée du développeur initial ; les modifications du repreneur ne doivent jamais y être poussées. Fais forker le dépôt vers son compte : `gh repo fork alysquart/caneco-bt-tool --clone` (ou bouton Fork sur la page GitHub puis clone de son fork). Explique-lui en une phrase que le fork est sa propre copie : tout ce qu'il modifie reste sur son compte.
5. Après le clone, vérifie avec `git remote -v` que `origin` pointe vers **son** compte et non vers `alysquart/caneco-bt-tool`. Si `gh repo fork --clone` a ajouté un remote `upstream` vers le dépôt d'origine, laisse-le en lecture seule et ne pousse jamais dessus. Place-toi sur la branche `main` (dernière version stable).
6. Lis alors `CLAUDE.md`, `README.md` et `docs/DOCUMENTATION_TECHNIQUE.md` pour charger le contexte complet du projet. Pour toute la suite de ta collaboration avec cet utilisateur : tous les commits et push vont sur son fork uniquement.

### Étape 3 — Configuration et lancement

1. Crée les fichiers d'environnement depuis les modèles : `.env` depuis `.env.example` à la racine, et `backend/.env` depuis `backend/.env.example`. Les valeurs par défaut conviennent en local. La clé `ANTHROPIC_API_KEY` reste vide (l'outil fonctionne sans).
2. Lance `docker compose up -d`, attends que les trois conteneurs (postgres, backend, frontend) soient sains. Le premier démarrage télécharge les images et installe les dépendances : préviens l'utilisateur que cela peut prendre plusieurs minutes.
3. Vérifie toi-même :
   - `http://localhost:8000/api/health` retourne `{"status":"ok"}`
   - `http://localhost:5173` sert la page de connexion
4. Donne à l'utilisateur les comptes de démonstration (créés automatiquement au démarrage) et fais-lui tester une connexion dans son navigateur :
   - admin@actemium.fr / Demo2026! (administrateur)
   - be@actemium.fr / Demo2026! (Responsable d'Études)
   - chef@actemium.fr / Demo2026! (Chef de Chantier)
   - ra@actemium.fr / Demo2026! (Responsable d'Affaires)

### Étape 4 — Charger le cas pilote DACHSER

Guide l'utilisateur, connecté avec le compte BE, pour :

1. Ouvrir le projet DACHSER-L3, onglet Études, et uploader `data/seed/dachser/DATA_DACHSER_INDICE_B.XLS` (le fichier est dans le dépôt cloné). Vérifier que les lignes sont parsées et affichées.
2. Onglet Tableaux : lancer la génération des tableaux. Vérifier que la liste des tableaux (TGBT, TES1, ...) apparaît avec leurs QR codes.
3. S'il veut aller plus loin tout de suite : uploader le bordereau et lancer une vérification depuis l'onglet Vérifs.

### Étape 5 — Lien public permanent (ngrok)

Objectif : une URL publique stable, comme sur l'installation d'origine, pour que les QR codes scannés par téléphone fonctionnent et pour les démonstrations à distance.

1. Fais créer un compte ngrok gratuit : https://dashboard.ngrok.com/signup
2. Demande-lui de te transmettre deux choses, en lui donnant les liens :
   - son **authtoken** : https://dashboard.ngrok.com/get-started/your-authtoken (précise-lui de te le coller dans la conversation, il ne sera écrit dans aucun fichier du projet)
   - son **domaine statique gratuit** : https://dashboard.ngrok.com/domains (bouton New Domain ; le plan gratuit inclut un domaine fixe du type `xxxx.ngrok-free.dev`)
3. Enregistre l'authtoken en variable d'environnement utilisateur Windows (`setx NGROK_AUTHTOKEN "..."`), jamais dans le dépôt.
4. Mets en place le tunnel permanent vers le port 5173 avec son domaine statique :
   - méthode standard : binaire ngrok officiel (https://ngrok.com/download), commande `ngrok http 5173 --domain=<son-domaine>.ngrok-free.dev` ;
   - si le réseau bloque le téléchargement du binaire (cas des réseaux d'entreprise limités au port 443), bascule sur le SDK Node `@ngrok/ngrok` avec un script de lancement qui lit `NGROK_AUTHTOKEN` depuis l'environnement.
5. Configure le démarrage automatique à l'ouverture de session Windows (script dans le dossier `shell:startup`) avec relance automatique en cas de coupure. Rappelle la limite du plan gratuit : une seule instance de tunnel à la fois (en cas d'erreur ERR_NGROK_108 ou 334, tout fermer, attendre 40 secondes, relancer une seule instance).
6. Mets à jour `PUBLIC_BASE_URL` dans `docker-compose.yml` avec la nouvelle URL, recrée le backend (`docker compose up -d backend`), puis fais régénérer les tableaux depuis l'onglet Tableaux pour que les QR codes encodent la nouvelle URL.
7. Vérifie que l'URL publique répond, et fais scanner un QR code par l'utilisateur avec son téléphone pour valider de bout en bout (préviens-le de la page intermédiaire « Visit Site » de ngrok au premier accès).

### Étape 6 — Contrôle final et compte rendu

1. Lance la suite de tests backend (`docker compose exec backend pytest`) et signale le résultat.
2. Présente à l'utilisateur un récapitulatif final :
   - ce qui est installé et où ;
   - les URL locales et l'URL publique permanente ;
   - les comptes de démonstration ;
   - comment tout arrêter (`docker compose down`) et tout relancer (`docker compose up -d`) ;
   - les trois documents à lire pour la suite : `README.md`, `PRD.md`, `docs/DOCUMENTATION_TECHNIQUE.md`.
3. Propose-lui de continuer à travailler avec toi (Claude Code) sur ce projet : le fichier `CLAUDE.md` te charge automatiquement le contexte et les règles à chaque session.

### État final attendu (checklist de sortie)

- [ ] Fork créé sur le compte du repreneur, cloné en local, branche `main` ; `origin` pointe vers son fork et aucun push ne va vers le dépôt d'origine
- [ ] Fichiers `.env` créés, aucun secret commité
- [ ] Trois conteneurs Docker en fonctionnement
- [ ] Connexion réussie sur http://localhost:5173 avec un compte de démonstration
- [ ] Export CANECO DACHSER indice B chargé et parsé
- [ ] Tableaux générés avec leurs QR codes
- [ ] Tunnel ngrok permanent actif avec domaine statique, démarrage automatique configuré
- [ ] `PUBLIC_BASE_URL` à jour, QR code testé depuis un téléphone
- [ ] Tests backend passés
- [ ] Récapitulatif final remis à l'utilisateur
