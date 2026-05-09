# PROJECT_SETUP.md — Guide étape par étape

> Lis-moi en premier. Ce guide te dit exactement quoi faire, dans quel ordre, pour passer de zéro à la V1 fonctionnelle.

---

## Vue d'ensemble en 5 minutes

Ce que tu vas faire :

1. Installer les outils nécessaires sur ton ordinateur (Docker, Node, VS Code, Claude Code)
2. Préparer le dossier projet avec les documents de référence
3. Initialiser GitHub (optionnel mais recommandé)
4. Lancer Claude Code et lui donner le mega-prompt
5. Suivre la progression module par module

Total estimé : 30 minutes de setup, puis Claude Code travaille en autonomie.

---

## Étape 1 — Prérequis à installer

Tu n'as besoin que de **trois outils** :

### 1.1   Docker Desktop

Pour faire tourner Postgres et l'environnement complet sans installer la base de données à la main.

Télécharge depuis https://www.docker.com/products/docker-desktop/. Lance-le après installation, vérifie qu'il tourne (icône baleine dans la barre des tâches).

### 1.2   Node.js (version 20 LTS)

Pour le front-end React.

Télécharge depuis https://nodejs.org/. Choisis la version **LTS** (20.x). Vérifie après installation :

```bash
node --version    # devrait afficher v20.x.x
npm --version     # devrait afficher 10.x.x
```

### 1.3   Python (version 3.11)

Pour le back-end FastAPI.

Sur Windows : https://www.python.org/downloads/release/python-3119/ (cocher « Add Python to PATH » à l'installation).
Sur macOS : `brew install python@3.11`.

Vérifie :

```bash
python --version    # devrait afficher Python 3.11.x
```

### 1.4   VS Code

Tu l'as déjà. Sinon : https://code.visualstudio.com/.

### 1.5   Claude Code

Si tu ne l'as pas déjà installé :

```bash
npm install -g @anthropic-ai/claude-code
```

Vérifie :

```bash
claude --version
```

Authentifie-toi avec ton compte Claude Pro :

```bash
claude
```

(Au premier lancement il ouvre le navigateur pour l'authentification.)

### 1.6   GitHub CLI (optionnel)

Si tu veux pousser le code sur GitHub depuis le terminal :

```bash
# Windows : winget install --id GitHub.cli
# macOS : brew install gh
# Linux : voir https://github.com/cli/cli#installation
```

Authentifie-toi :

```bash
gh auth login
```

Choisis « GitHub.com », « HTTPS », « Yes » pour authentifier git, et « Login with a web browser ».

---

## Étape 2 — Préparer le dossier projet

### 2.1   Créer le dossier

Choisis un emplacement sur ton ordinateur. Par exemple :

- Windows : `C:\Users\<toi>\Documents\projets\caneco-bt-tool`
- macOS / Linux : `~/Documents/projets/caneco-bt-tool`

Crée-le (depuis ton explorateur de fichiers ou un terminal).

### 2.2   Y placer les documents de référence

Dans ce dossier, crée la sous-arborescence suivante :

```
caneco-bt-tool/
├── docs/
│   ├── PRD.md                         (livré)
│   ├── cahier_des_charges.md          (à convertir depuis le DOCX)
│   ├── cartes_empathie.md             (à convertir depuis le DOCX)
│   └── brief_pitch.md                 (à convertir depuis le DOCX)
├── data/
│   └── seed/
│       └── dachser/
│           ├── DATA_DACHSER_INDICE_B.XLS
│           ├── Pièce_03_Bordereau_des_Prix_DACHSER_LOT3.xlsx
│           ├── Pièce_021_Clauses_techniques_DACHSER_LOT3.pdf
│           └── Pièce_02-2_Descriptif_des_ouvrages_DACHSER_LOT3.pdf
├── assets/
│   ├── logo_vinci-removebg-preview.png
│   └── logo_vinci_actemium_fond_blanc.png
├── CLAUDE.md                          (livré)
├── PROMPT_CLAUDE_CODE.md              (livré)
├── SECURITY_AUDIT_PROMPT.md           (livré, à utiliser avant chaque tag)
└── PROJECT_SETUP.md                   (ce fichier)
```

**Ce qu'il faut faire concrètement** :

1. Place les **5 fichiers livrés** (PRD.md, CLAUDE.md, PROMPT_CLAUDE_CODE.md, SECURITY_AUDIT_PROMPT.md, PROJECT_SETUP.md) à la racine et dans `docs/`.
2. Place les **4 fichiers DACHSER** (les pièces de marché et l'export CANECO) dans `data/seed/dachser/`. Tu peux les copier depuis ta base de connaissance projet.
3. Place les **2 logos VINCI** dans `assets/`.
4. Pour les 3 documents `cahier_des_charges.md`, `cartes_empathie.md`, `brief_pitch.md` : tu peux soit les laisser au format DOCX et dire à Claude Code de les lire (il sait), soit les convertir rapidement en markdown via Pandoc (`pandoc 02_Cahier_des_Charges_VEAO_2026.docx -o cahier_des_charges.md`). Pour la V1, **garder le DOCX** est suffisant : on demande à Claude Code de lire le DOCX directement.

> Astuce : tu peux laisser les DOCX à la racine du dossier projet. Claude Code les lira sans problème.

### 2.3   Ouvrir le dossier dans VS Code

```bash
cd ~/Documents/projets/caneco-bt-tool
code .
```

(Ou `Fichier > Ouvrir le dossier...` dans VS Code.)

---

## Étape 3 — GitHub (optionnel mais recommandé)

### 3.1   Pourquoi GitHub

- **Sauvegarde** : si ton ordinateur plante, ton code n'est pas perdu
- **Historique** : tu peux revenir en arrière à tout moment
- **Partage avec ton encadrant** : il peut voir le code, faire des commentaires
- **Démonstration** : utile pour montrer ton travail au jury et pour les futurs employeurs

### 3.2   Création du dépôt

Si GitHub CLI est installé et tu es authentifié, **dis simplement à Claude Code** au début du Bloc 1 :

> Je veux que ce projet soit hébergé sur mon GitHub `alysquart`. Crée d'abord un dépôt GitHub privé nommé `caneco-bt-tool` via `gh repo create alysquart/caneco-bt-tool --private --source=. --remote=origin`, puis configure git pour pousser à chaque commit.

Claude Code s'en occupe.

Si tu préfères créer manuellement :
1. Va sur https://github.com/new
2. Nom du dépôt : `caneco-bt-tool`
3. Sélectionne **Private** (ne pas rendre public à ce stade — données sensibles VINCI)
4. **Ne coche pas** « Add a README file » (le projet en a déjà un)
5. Crée le dépôt
6. Suis les instructions affichées pour pousser un dépôt local existant (Claude Code le fera automatiquement après init git)

### 3.3   Si tu ne veux pas GitHub

Tout fonctionne en local. Tu peux toujours pousser plus tard. Le projet est complet sans GitHub.

---

## Étape 4 — Skills Claude Code recommandées

Claude Code a un système de **skills** (extensions) qui ajoutent des capacités spécifiques. Voici celles qui sont vraiment utiles pour ce projet :

### 4.1   Skills à installer

À installer dans Claude Code en lui demandant simplement :

> Installe les skills suivantes : obra/superpowers, anthropics/frontend-design, anthropics/security-guidance, anthropics/code-review.

Ces skills te donnent :

| Skill | Apport |
|---|---|
| `obra/superpowers` | Améliorations générales de productivité |
| `anthropics/frontend-design` | Aide pour le design frontend (cohérent avec ton besoin de "pas d'AI slop", design pro à l'image VINCI) |
| `anthropics/security-guidance` | Conseils de sécurité automatiques (auth, CORS, secrets) |
| `anthropics/code-review` | Auto-review avant chaque commit |

> Toutes ces skills sont gratuites.

### 4.2   Skills à NE PAS installer

Reste sur l'essentiel. Évite les skills exotiques (oh-my-cloud et compagnie) qui ne servent pas pour ce projet et peuvent créer du bruit.

### 4.3   Comment vérifier qu'une skill est bien installée

Dans Claude Code :

```
/skills list
```

---

## Étape 5 — Lancer Claude Code

### 5.1   Démarrer Claude Code dans le dossier

```bash
cd ~/Documents/projets/caneco-bt-tool
claude
```

### 5.2   Coller le Bloc 1

Ouvre le fichier `PROMPT_CLAUDE_CODE.md`, copie tout le contenu **entre `===== DÉBUT BLOC 1 =====` et `===== FIN BLOC 1 =====`** (sans inclure ces deux lignes), et colle-le dans Claude Code.

Appuie sur Entrée. Claude Code va :
1. Lire les documents du dossier `docs/`
2. Te confirmer qu'il a compris le projet
3. Initialiser le dépôt git
4. Créer toute la structure de dossiers
5. Configurer le back-end Python et le front-end React
6. Lancer `docker compose up -d` pour vérifier que tout démarre

**Tu n'as rien à faire** pendant cette phase, sauf répondre aux questions ponctuelles de Claude Code (par exemple s'il te demande confirmation pour installer une dépendance).

Cette étape prend **15 à 30 minutes** selon ta connexion.

### 5.3   Validation après Bloc 1

Vérifie manuellement que :

```bash
# Test 1 : les conteneurs tournent
docker compose ps

# Test 2 : le back-end répond
curl http://localhost:8000/api/health
# devrait retourner {"status":"ok"}

# Test 3 : le frontend s'affiche
# Ouvre http://localhost:5173 dans ton navigateur
```

Si tout est OK, passe au Bloc 2.

### 5.4   Coller le Bloc 2

Ouvre `PROMPT_CLAUDE_CODE.md`, copie le contenu entre `===== DÉBUT BLOC 2 =====` et `===== FIN BLOC 2 =====`, et colle-le dans Claude Code.

Claude Code va développer **module par module** (6 modules au total). À la fin de chaque module, il te demande validation. Réponds simplement « OK continue » ou pose des questions si quelque chose ne te convient pas.

**Durée estimée** : 1h30 à 3h selon la rapidité de Claude Code et la complexité des choix techniques.

---

## Étape 6 — Pendant que Claude Code travaille

### 6.1   Ce que tu peux faire en parallèle

- Préparer le pitch (relire le brief PPT, t'entraîner à parler)
- Générer les images Nano Banana (suivre les prompts du brief)
- Prendre une photo des étiquettes QR de référence pour le rendu
- Préparer ta démo : à la fin tu vas vouloir montrer l'outil au jury

### 6.2   Comment surveiller la progression

Dans Claude Code, tu vois en temps réel chaque action. Si quelque chose te paraît bizarre, tu peux dire :

> Stop, peux-tu m'expliquer ce que tu fais ? Je n'ai pas compris cette décision.

Claude Code te répond, et tu décides si tu valides ou si tu changes de cap.

### 6.3   Si Claude Code se trompe

Ça arrive. Trois recours :

1. **Annuler la dernière action** : Ctrl+C dans Claude Code, puis « Annule le dernier commit et reviens à l'état d'avant ».
2. **Corriger en local** : tu peux éditer un fichier dans VS Code et dire à Claude Code « J'ai modifié le fichier X, continue à partir de là ».
3. **Reprendre à zéro un module** : « Annule tout ce qui a été fait sur le Module 3, recommençons-le. Voici ce qui n'allait pas : [explication] ».

### 6.4   Si tu manques de crédits Claude Pro

Claude Pro a des limites de session. Si tu approches la limite :

1. Dis à Claude Code : « Récapitule en 10 lignes l'état exact du projet : ce qui est fait, ce qu'il reste à faire, et où nous en sommes dans le module en cours. ».
2. Sauvegarde cette réponse dans `docs/STATE.md`.
3. Ferme Claude Code, attends le reset (ou prends une pause).
4. Au retour, ouvre Claude Code dans le même dossier, et dis « Reprends le projet où on s'est arrêté. Lis `docs/STATE.md` pour le contexte. ».

Claude Code lit `CLAUDE.md` automatiquement à chaque session, donc le contexte est préservé.

---

## Étape 7 — Validation V1

À la fin du Bloc 2, tu dois pouvoir :

1. Te connecter à http://localhost:5173 avec `admin@actemium.fr` / `Demo2026!`
2. Voir la liste des projets, dont le projet « DACHSER — Lot 3 Électricité » de démo
3. Cliquer sur le projet → onglet Études → uploader le fichier `DATA_DACHSER_INDICE_B.XLS`
4. Voir les 700 lignes parsées dans une table
5. Uploader le bordereau, lancer la vérification, voir le rapport d'écarts
6. Aller sur l'onglet Tableaux, générer la planche A4 de QR codes, télécharger le PDF
7. Scanner un QR code avec ton téléphone → voir la fiche tableau au format mobile
8. Aller sur l'onglet DOE → générer le DOE → télécharger le PDF complet

Si tout fonctionne : **avant de tagger v0.1.0, fais l'audit de sécurité** (étape 7 bis ci-dessous).

---

## Étape 7 bis — Audit de sécurité avant le tag v0.1.0

C'est une étape **non négociable**. Le projet manipule des données projet VINCI sensibles. Le code a été en partie « vibe-codé » avec Claude Code, ce qui introduit régulièrement des failles classiques (secrets en dur, validation manquante, CORS large, etc.).

### Ce que tu fais concrètement

1. Crée une branche d'audit dans le terminal (toujours dans le dossier projet) :

```bash
git checkout -b audit/security-v1
```

2. Lance Claude Code dans cette branche :

```bash
claude
```

3. Ouvre `SECURITY_AUDIT_PROMPT.md`. Copie tout le contenu **entre les lignes `===== DÉBUT PROMPT =====` et `===== FIN PROMPT =====`** (sans inclure ces deux lignes). Colle dans Claude Code.

4. Claude Code va :
   - Lire l'intégralité du code (15 minutes)
   - Te présenter en 10 lignes son modèle mental de l'architecture
   - Dérouler les 9 sections de checklist (45 vérifications environ)
   - Te livrer un rapport structuré avec le niveau de sécurité (🔴 / 🟠 / 🟡 / 🟢)
   - Lister les conclusions CRITIQUE / HAUTE / MOYENNE / BASSE
   - Proposer un plan de remédiation priorisé

5. **Aucune conclusion CRITIQUE ne doit rester ouverte avant le tag v0.1.0.** Les conclusions HAUTES sont corrigées immédiatement.

6. Réponds à Claude Code : « Corrige toutes les conclusions CRITIQUES et HAUTES. Pour les MOYENNES et BASSES, propose un commit séparé que je validerai à part. »

7. Claude Code applique les corrections. Lance la suite de tests complète (`pytest`, `pnpm test`) pour vérifier que rien n'est cassé.

8. Sauvegarde le rapport d'audit :

```bash
mkdir -p docs/security_audits
# Le rapport est généralement dans la conversation. Demande à Claude Code :
# "Exporte le rapport d'audit complet dans docs/security_audits/2026-XX-XX_audit_v0.1.0.md"
```

9. Merge la branche dans `main` :

```bash
git checkout main
git merge audit/security-v1
git push  # si tu utilises GitHub
```

10. Tagge la version :

```bash
git tag -a v0.1.0 -m "Première version pilote livrée pour la soutenance VEAO 2026, audit de sécurité validé"
git push --tags
```

### Pourquoi cette étape est un atout pour ton pitch

L'audit de sécurité est un **point fort** du dossier face au jury VEAO. Il montre :
- Que ce n'est pas une preuve de concept jetable
- Que tu as anticipé les enjeux de production
- Que tu maîtrises la gouvernance d'un projet d'IA appliquée

Si pendant le pitch on te demande « Comment garantissez-vous que l'outil ne fuit pas les données projet ? », tu réponds :

> « Nous avons appliqué un audit de sécurité systématique sur 9 sections critiques avant chaque release. Le rapport d'audit est versionné dans le dépôt et signé pour chaque tag. »

Cette réponse impressionne le jury plus qu'une démo technique.

---

## Annexe — Commandes utiles

### Démarrer / arrêter le projet

```bash
docker compose up -d         # démarre tout en arrière-plan
docker compose logs -f       # voir les logs en direct
docker compose down          # arrête tout
docker compose down -v       # arrête tout ET supprime la base (attention !)
```

### Tests

```bash
cd backend && pytest                    # lance les tests Python
cd backend && pytest -k test_caneco     # lance uniquement les tests CANECO
cd frontend && pnpm test                # lance les tests React
```

### Nettoyer le projet

```bash
docker compose down -v                  # remet la base à zéro
rm -rf backend/__pycache__              # nettoie le cache Python
```

### Réinitialiser la base de données (perte de toutes les données)

```bash
docker compose down -v
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

---

## Annexe — Que faire si...

### ... Claude Code refuse une commande

Il a probablement détecté un risque (clé API exposée, suppression d'un fichier important). Lis son explication et adapte la demande.

### ... Le port 8000 ou 5173 est déjà occupé

Modifie le `docker-compose.yml` pour changer les ports (par exemple `8001:8000`). Demande à Claude Code de le faire.

### ... Tu vois une erreur « Cannot connect to Docker daemon »

Docker Desktop n'est pas lancé. Lance-le, attends que la baleine soit verte, retry.

### ... Le frontend ne se rafraîchit pas automatiquement

Hot reload est cassé. Redémarre le conteneur frontend : `docker compose restart frontend`.

### ... Tu veux montrer le projet à ton encadrant

Soit tu lui pousses le code sur GitHub et tu lui partages le lien, soit tu fais une démo en partage d'écran. Le projet tourne en local sur ton ordinateur.

### ... Ton encadrant veut tester l'outil sur son ordinateur

Il clone le dépôt GitHub, fait `docker compose up -d`, et c'est tout. La stack est conçue pour être 100 % portable.

---

**Tu as tout ce qu'il faut. Prends une grande respiration, et lance-toi.**

**Bonne soutenance.**
