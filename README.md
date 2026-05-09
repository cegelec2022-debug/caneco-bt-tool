# Valorisation des données CANECO BT

Outil de gestion et de valorisation des données issues de CANECO BT pour le Challenge Innovation VEAO 2026 (Actemium Cegelec — VINCI Energies). De la note CANECO BT au DOE livré au client, chaque mètre de câble est tracé, vérifié et croisé avec les autres sources de vérité du projet (CPS, bordereau, norme NF C 15-100). L'outil s'organise en trois briques : agent de vérification, tableau de bord multi-projets avec saisie chantier mobile, et générateur de QR codes et de DOE. Le cas pilote est le projet DACHSER — Lot 3 Électricité.

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (requis — inclut docker compose)
- [Node.js 20 LTS](https://nodejs.org/) ou supérieur
- [Python 3.11](https://www.python.org/downloads/)
- [pnpm](https://pnpm.io/) — `npm install -g pnpm`

---

## Démarrage en développement

```bash
# 1. Copier et remplir les variables d'environnement
cp .env.example .env
cp backend/.env.example backend/.env

# 2. Démarrer tous les services (postgres + backend + frontend)
docker compose up -d

# 3. Vérifier que tout tourne
docker compose ps
```

L'application est accessible sur :
- Frontend : http://localhost:5173
- API REST : http://localhost:8000/api/docs (Swagger)
- Healthcheck : http://localhost:8000/api/health

---

## Lancer les tests

```bash
# Tests backend (Python)
cd backend && pytest

# Tests backend avec couverture
cd backend && pytest --cov=app --cov-report=term-missing

# Tests frontend (Vitest)
cd frontend && pnpm test
```

---

## Commandes Docker utiles

```bash
docker compose up -d          # Démarrer en arrière-plan
docker compose logs -f        # Voir les logs en temps réel
docker compose down           # Arrêter les services
docker compose down -v        # Arrêter et supprimer la base de données
docker compose restart backend # Redémarrer uniquement le backend
```

---

## Documents de référence

- [PRD — Vision produit](docs/PRD.md)
- [CLAUDE.md — Conventions et garde-fous](docs/CLAUDE.md)
- [PROMPT_CLAUDE_CODE.md — Plan de développement](docs/PROMPT_CLAUDE_CODE.md)
- [SECURITY_AUDIT_PROMPT.md — Audit de sécurité](docs/SECURITY_AUDIT_PROMPT.md)

---

## Structure du projet

```
caneco-bt-tool/
├── backend/          Python 3.11 + FastAPI + SQLAlchemy
├── frontend/         React 18 + TypeScript + Tailwind + shadcn/ui
├── data/seed/        Fichiers de référence DACHSER (XLS, XLSX, PDF)
├── docs/             Documentation projet
└── docker-compose.yml
```
