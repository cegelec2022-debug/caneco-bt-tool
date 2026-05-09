# Valorisation des donnees CANECO BT

Outil de gestion et de valorisation des donnees issues de CANECO BT, developpe dans le cadre du Challenge Innovation VEAO 2026 par Actemium Cegelec — VINCI Energies.

L'outil transforme le cable en donnee pilotee de bout en bout : de la note CANECO BT au DOE livre au client, chaque metre de cable est trace, verifie et croise avec les autres sources de verite du projet (CPS, bordereau, norme NF C 15-100).

Il s'organise en trois briques connectees : un agent de verification CANECO, un tableau de bord multi-projets avec saisie chantier mobile, et un generateur de QR codes et de DOE.

Le cas pilote est le projet DACHSER — Lot 3 Electricite (700 lignes CANECO, 244 lignes bordereau).

---

## Documents de reference

- [PRD — Vision produit](docs/PRD.md)
- [CLAUDE.md — Conventions et garde-fous](docs/CLAUDE.md)
- [PROMPT_CLAUDE_CODE.md — Plan de developpement](docs/PROMPT_CLAUDE_CODE.md)
- [SECURITY_AUDIT_PROMPT.md — Audit de securite](docs/SECURITY_AUDIT_PROMPT.md)

---

## Demarrage rapide

Le setup technique (FastAPI, React, Docker, base de donnees) sera mis en place dans la prochaine etape via le Bloc 1 du fichier `PROMPT_CLAUDE_CODE.md`.

Prerequis a installer avant de commencer :
- Docker Desktop
- Node.js 20 LTS
- Python 3.11
- GitHub CLI (`gh`)

---

## Stack technique

- Back-end : Python 3.11 + FastAPI + PostgreSQL 16
- Front-end : React 18 + TypeScript + TailwindCSS + shadcn-ui
- Conteneurisation : Docker + docker-compose
- Authentification : JWT (python-jose + bcrypt)
