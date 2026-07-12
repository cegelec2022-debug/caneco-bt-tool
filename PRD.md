# PRD — Valorisation des données CANECO BT

**Projet** : Outil de valorisation des données CANECO BT
**Cas pilote** : projet DACHSER — Lot 3 (Électricité)
**Agence** : Actemium Cegelec — VINCI Energies
**Cadre** : Challenge Innovation VEAO 2026
**Statut** : V1 livrée (soutenance VEAO et soutenance PFE du 02/07/2026 passées) — base d'évolution vers le déploiement agence
**Date** : Mai 2026 (création) — mise à jour Juillet 2026
**Version** : 1.1

---

## 1. Vision produit

Maîtriser le câble, c'est maîtriser le projet.

Aujourd'hui dans les projets électriques tertiaires et industriels, le câble représente une part majeure du chiffre d'affaires du lot électricité. Il est calculé précisément en phase d'études (CANECO BT), commandé en gros en phase achat (bordereau), tiré sur le terrain selon les contraintes physiques du chantier, puis reconstitué tant bien que mal en clôture pour le DOE. Entre ces étapes, aucune continuité numérique. Le résultat : du temps perdu en vérifications manuelles, des écarts financiers découverts trop tard, et des dossiers d'ouvrages exécutés peu fiables.

Notre outil transforme le câble en donnée pilotée de bout en bout. De la note CANECO BT au DOE livré au client, chaque mètre de câble est tracé, vérifié, et croisé avec les autres sources de vérité du projet (CPS, bordereau, norme NF C 15-100). L'outil s'organise en trois briques connectées, autour d'une base de données unique, accessibles selon le rôle de l'utilisateur.

L'ambition à 12 mois : être déployé sur trois agences VINCI Energies BT et constituer la première référence interne de pilotage du câble.

---

## 2. Personas et besoins

### 2.1   Responsable d'Études (BE)

Persona principal du module de vérification.

| Aspect | Description |
|---|---|
| Quotidien | Calcule sur CANECO BT, rédige les notes, croise avec le CPS et le bordereau |
| Outils actuels | CANECO BT, Excel, PDF du CPS, plans Autocad |
| Frein principal | Vérifications manuelles répétitives, peur de valider une étude qui sera remise en cause sur chantier |
| Gain attendu | 60 à 80 % de temps gagné en phase de vérification, fiabilité accrue |
| Mode d'usage | Au bureau, sur poste de travail, à chaque indice de calcul (souvent A, B, C, D) |

### 2.2   Chef de Chantier

Persona principal de l'application mobile terrain.

| Aspect | Description |
|---|---|
| Quotidien | Coordonne les équipes, tire les câbles selon les contraintes physiques, ajuste en temps réel |
| Outils actuels | Téléphone, WhatsApp, Excel partagé, fiches papier |
| Frein principal | Pas d'outil mobile adapté, traçabilité perdue lors des imprévus |
| Gain attendu | Saisie en 3 clics, accès aux fiches via QR code, justification photo des écarts |
| Mode d'usage | Sur le chantier, avec gants et EPI, parfois en zone à faible connexion |

### 2.3   Responsable d'Affaires (RA)

Persona principal du tableau de bord multi-projets.

| Aspect | Description |
|---|---|
| Quotidien | Pilote plusieurs chantiers, valide les commandes, négocie avec le client |
| Outils actuels | ERP, Excel, mails, points hebdo téléphoniques |
| Frein principal | Vision fragmentée, dérapages découverts trop tard |
| Gain attendu | Tableau de bord temps réel, alertes proactives, arbitrage inter-projets |
| Mode d'usage | Au bureau, sur poste de travail, en consultation quotidienne |

### 2.4   Hors périmètre V1

- L'acheteur / magasinier n'est pas utilisateur direct. Le RA reste le point de contact.
- Le client final ne se connecte pas à l'outil. Il reçoit le DOE généré.

---

## 3. Périmètre fonctionnel V1

### 3.1   Brique 1 — Agent de vérification CANECO

Comparaison automatique de la note CANECO BT avec les autres sources de vérité du projet.

**Entrées**
- Export CANECO BT (.xls ou .xlsx) — 23 colonnes typées (Repère, Désignation, Style, Nb récepteurs, Consommation, IB, Longueur, Type de câble, Câble, Neutre, PE, Ame, Calibre, Bloc déclencheur, IrTh, IrMg, Icu, etc.)
- CPS du projet (.pdf) — exigences contractuelles client
- Bordereau de prix (.xlsx) — feuille « BDP_ELECTRICITE CFO » dans le cas DACHSER (244 lignes, 6 colonnes)
- Référentiel NF C 15-100 — règles intégrées en dur dans l'application (chute de tension, sections minimales, calibres maximums, protections différentielles)

**Traitements**
- Parsing structuré des trois fichiers
- Rapprochement ligne CANECO ↔ ligne bordereau par repère + type de câble + section, avec score de confiance
- Application des 10 codes de gestion d'écart (E-001 à E-010, voir cahier des charges section 5.2)
- Vérification normative NF C 15-100
- Suggestions de bonnes pratiques (alertes non bloquantes)
- Couche IA optionnelle (API Claude) pour les bordereaux PDF non structurés

**Sorties**
- Rapport d'écarts horodaté, filtrable par criticité (bloquant, à corriger, à signaler, information)
- Export Excel et PDF
- Indicateur de complétude global (% d'écarts levés)

### 3.2   Brique 2 — Tableau de bord multi-projets et suivi de chantier

Pilotage temps réel des projets et remontée de l'information chantier.

**Tableau de bord (RA)**
- Vue d'ensemble : nombre de projets actifs, écarts ouverts, alertes critiques, marge globale prévisionnelle
- Liste des projets : code, client, agence, avancement physique, écarts ouverts, alertes, marge
- Drill-down sur un projet : KPI prévu / réalisé sur les câbles, indicateur DOE
- Module de transfert de matériel inter-projets

**Saisie chantier (Chef de Chantier)**
- Application web responsive (PWA), accessible sur smartphone
- Mode hors-ligne : la saisie reste possible sans réseau, synchronisation différée au retour
- Saisie en 3 clics : sélection du tableau (par scan QR ou liste) → sélection du départ → saisie de la longueur
- Possibilité d'ajouter une photo et un commentaire en justification
- Notification des autres parties prenantes en temps réel après synchronisation

**Calculs automatiques**
- Écart par départ, par tableau, par projet (longueur prévue CANECO vs longueur réalisée chantier)
- Alertes sur dépassement de seuil (ex. +10 % de surconsommation sur un tableau)
- Détection de surplus disponibles pour transfert vers un autre projet

### 3.3   Brique 3 — Carnet des câbles évolutif et QR codes

Constitution du DOE en continu et étiquetage physique des tableaux.

**QR codes**
- Génération automatique d'un QR code par tableau, à partir des données du projet
- L'URL pointe vers la fiche tableau accessible en lecture (sans authentification — mais token aléatoire long pour limiter la diffusion)
- Pages d'impression A4 contenant **plusieurs étiquettes par feuille** (8 ou 12 selon taille), prêtes à découper et coller sur les armoires
- Chaque étiquette comprend : QR code (avec logo Cegelec au centre), repère du tableau (TGBT, TES1, TINFO, etc.), nom du projet, mention « Cegelec — VINCI Energies »

**Fiche tableau (page web accessible par scan)**
- En-tête rouge VINCI / Cegelec
- Repère et désignation du tableau (ex. « TGBT — Tableau Général Basse Tension »)
- Tableau récapitulatif des données issues de CANECO : Repère, Désignation, Style, Nb récepteurs, Consommation, IB, Longueur, Type de câble, Câble, Neutre, PE ou PEN, Calibre, Bloc de coupure, Bloc déclencheur, Bloc différentiel, IrTh / IN, IrMg / IN
- Bouton « Voir le PDF » pour télécharger la fiche en PDF (utile pour les rapports d'audit ou la transmission au client)
- Affichage responsive optimisé mobile

**DOE auto-généré**
- Bouton « Générer le DOE » dans la page projet
- Production d'un fichier PDF complet : page de garde, table des matières, fiches de chaque tableau, longueurs prévues vs réalisées, photos terrain, écarts levés / non levés
- Production d'un fichier Excel parallèle pour les données brutes
- Versionning : chaque génération crée une nouvelle version, traçable dans l'historique

---

## 4. Métriques de succès

### 4.1   Métriques fonctionnelles V1 (sur projet pilote DACHSER)

| Métrique | Cible | Mesure |
|---|---|---|
| Temps de parsing d'un export CANECO de 700 lignes | < 5 s | Sur poste de développement standard |
| Temps de génération d'un rapport d'écarts complet | < 10 s | Idem |
| Taux de rapprochement automatique CANECO ↔ bordereau | > 80 % | Sur le jeu DACHSER, validation manuelle |
| Couverture des codes d'écart E-001 à E-010 | 100 % | 8 scénarios de recette validés |
| Affichage du tableau de bord 5 projets fictifs | < 2 s | Idem |
| Délai d'aller-retour saisie mobile ↔ tableau de bord | < 30 s | En ligne |
| Génération du DOE PDF + Excel | < 30 s | Idem |

### 4.2   Métriques métier post-déploiement

À mesurer dans les 3 mois suivant le déploiement sur les premiers projets réels :

| Métrique | Cible attendue | Méthode |
|---|---|---|
| Temps de vérification BE par projet | -60 % minimum | Comparaison avec et sans outil sur projets équivalents |
| Nombre d'écarts détectés en phase études | +30 % | Comparaison historique |
| Surconsommation câble en chantier | -5 à -15 % | Comparaison historique |
| Délai de production du DOE | de plusieurs semaines à 1 jour | Mesure simple |

### 4.3   Métriques d'adoption

| Métrique | Cible 6 mois |
|---|---|
| Nombre de projets actifs sur la plateforme | 5 |
| Nombre de Chefs de Chantier ayant saisi au moins une fois | 3 |
| Taux de satisfaction (survey simple) | > 80 % |

---

## 5. Choix technologiques

Tous les composants sont open source et gratuits. Aucune licence à acheter.

### 5.1   Stack

| Couche | Technologie | Justification |
|---|---|---|
| Back-end | Python 3.11 + FastAPI | Productif, écosystème data riche, parfait pour Excel et PDF |
| Lecture Excel | openpyxl, xlrd, pandas | Standards, gèrent .xls et .xlsx |
| Lecture PDF | pdfplumber, pypdf | Extraction texte et tableaux |
| Base de données | PostgreSQL 16 | Robuste, gratuit, support JSON |
| ORM | SQLAlchemy 2.x | Standard Python |
| Migrations | Alembic | Standard SQLAlchemy |
| Authentification | FastAPI Users (JWT) | Intégré FastAPI |
| Front-end web | React 18 + Vite + TypeScript | Productivité, robustesse |
| UI | TailwindCSS + shadcn/ui | Design sobre, professionnel, prêt à l'emploi |
| State management | TanStack Query (React Query) | Standard moderne pour API REST |
| Application mobile | PWA (même base React) | Pas de double code, accès caméra natif via getUserMedia |
| QR codes | qrcode (back-end Python) + html5-qrcode (front-end) | Standards open source |
| Génération PDF | ReportLab (back-end) | Pour DOE et fiches tableau |
| Couche IA | API Anthropic (Claude) — optionnelle | Pour bordereaux PDF non structurés et formulation des écarts |
| Conteneurisation | Docker + docker-compose | Déploiement reproductible |
| Hébergement | Local (dev) + Render plan free (recette) | Conforme contrainte zéro coût |

### 5.2   Architecture en couches

```
┌─────────────────────────────────────────┐
│   Front-end React (web + PWA mobile)    │
│   TailwindCSS + shadcn/ui               │
└────────────────┬────────────────────────┘
                 │ HTTPS / JSON
┌────────────────▼────────────────────────┐
│   API FastAPI                           │
│   - Routers : auth, projects, caneco,   │
│     bordereau, cps, verifications,      │
│     gaps, tableaux, departures,         │
│     field-entries, dashboard, doe       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│   Services métier                       │
│   - CanecoParser, BordereauParser,      │
│     CpsParser                           │
│   - VerificationEngine                  │
│   - NormChecker (NF C 15-100)           │
│   - DoeGenerator                        │
│   - QrLabelGenerator                    │
│   - LlmAdapter (optionnel)              │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│   Persistence : PostgreSQL              │
│   13 entités principales                │
│   (voir cahier des charges § 6.3)       │
└─────────────────────────────────────────┘
```

### 5.3   Architecture de l'agent IA

L'agent intelligent **n'est pas une boîte noire LLM**. C'est un moteur déterministe (règles métier explicites) avec une couche LLM en **adapter optionnel** pour les cas non structurés.

**Pourquoi ce choix**
1. La fiabilité des contrôles techniques exige des règles explicites, auditables, modifiables sans réentraînement.
2. La norme NF C 15-100 est un texte précis : tabuler les règles dans le code est plus sûr qu'un prompt.
3. Le LLM coûte cher en API si on l'appelle à chaque comparaison de ligne.
4. La performance : un moteur déterministe traite 700 lignes en 2 secondes ; un LLM prendrait des minutes.

**Composants**
- `VerificationEngine` (orchestrateur) : pilote l'enchaînement des vérifications
- `LineMatcher` : rapprochement ligne CANECO ↔ ligne bordereau (Jaro-Winkler + règles métier)
- `NormChecker` : vérification NF C 15-100 (table de règles JSON modifiable)
- `CpsRuleExtractor` : extrait les exigences chiffrables d'un CPS (mode déterministe + fallback LLM)
- `LlmAdapter` (optionnel) : appel API Claude pour reformulation en langage naturel et lecture de PDF non structurés
- `GapEmitter` : émet les écarts au format normalisé (E-001 à E-010)

**Mode dégradé**
- Si l'API Claude n'est pas configurée (clé absente), l'outil fonctionne en mode 100 % déterministe. Aucune fonction critique n'en dépend.

---

## 6. User stories prioritaires (V1)

Format : « En tant que [persona], je veux [action] afin de [bénéfice]. »

### 6.1   Responsable d'Études

- **US-BE-01** En tant que BE, je veux uploader la note CANECO indice B du projet DACHSER, afin que l'outil parse les 700 lignes en moins de 5 secondes.
- **US-BE-02** En tant que BE, je veux uploader le bordereau Excel du projet, afin de pouvoir lancer la vérification croisée.
- **US-BE-03** En tant que BE, je veux uploader le CPS PDF, afin que l'outil extraie automatiquement les exigences chiffrables (sections minimales, types de câble imposés).
- **US-BE-04** En tant que BE, je veux lancer une vérification complète, afin d'obtenir un rapport d'écarts en moins de 10 secondes.
- **US-BE-05** En tant que BE, je veux filtrer le rapport d'écarts par criticité (bloquant, à corriger, à signaler), afin de traiter les écarts dans le bon ordre.
- **US-BE-06** En tant que BE, je veux lever ou justifier un écart en y associant un commentaire, afin de garder la traçabilité de mes décisions.
- **US-BE-07** En tant que BE, je veux exporter le rapport d'écarts en PDF, afin de l'envoyer aux autres parties prenantes.
- **US-BE-08** En tant que BE, je veux comparer deux indices CANECO (par exemple A et B), afin de voir ce qui a changé entre deux versions.

### 6.2   Chef de Chantier

- **US-CC-01** En tant que Chef de Chantier, je veux scanner un QR code apposé sur un tableau, afin d'accéder à la fiche du tableau en moins de 2 secondes.
- **US-CC-02** En tant que Chef de Chantier, je veux saisir la longueur réellement tirée sur un départ, afin que le BE et le RA en soient informés en temps réel.
- **US-CC-03** En tant que Chef de Chantier, je veux ajouter une photo en justification d'un écart, afin de documenter les contraintes terrain.
- **US-CC-04** En tant que Chef de Chantier, je veux pouvoir saisir hors connexion, afin de continuer mon travail en zone à faible réseau.
- **US-CC-05** En tant que Chef de Chantier, je veux voir mes saisies en attente de synchronisation, afin de savoir ce qui a été remonté ou non.

### 6.3   Responsable d'Affaires

- **US-RA-01** En tant que RA, je veux voir un tableau de bord de tous mes projets, afin d'identifier en un coup d'œil ceux qui dérapent.
- **US-RA-02** En tant que RA, je veux drill-down sur un projet, afin de voir les écarts détaillés sur les câbles.
- **US-RA-03** En tant que RA, je veux recevoir une alerte automatique en cas de dépassement de seuil, afin de réagir avant qu'il ne soit trop tard.
- **US-RA-04** En tant que RA, je veux déclencher la génération du DOE en fin de chantier, afin de le livrer au client sans phase de reconstruction.
- **US-RA-05** En tant que RA, je veux générer une planche A4 contenant 8 ou 12 QR codes des tableaux d'un projet, afin de les imprimer et coller en chantier.
- **US-RA-06** En tant que RA, je veux arbitrer un transfert de matériel entre projets, afin d'éviter les pertes sèches.

---

## 7. Identité visuelle

L'outil reprend la charte VINCI Energies / Cegelec. Aucune fantaisie graphique. Sobriété et professionnalisme.

### 7.1   Couleurs

| Usage | Code hex | Notes |
|---|---|---|
| Rouge VINCI (accent principal) | `#C8102E` | Boutons primaires, alertes critiques, en-têtes |
| Bleu nuit VINCI | `#001E50` | Titres, navigation, badges |
| Texte principal | `#1A1A1A` | Corps de texte |
| Texte secondaire | `#374151` | Sous-titres, légendes |
| Texte tertiaire | `#6B7280` | Métadonnées, footers |
| Fond clair | `#FAFAFA` | Fond de page |
| Fond cellule alternée | `#F5F5F5` | Tableaux zébrés |
| Bordure standard | `#BFBFBF` | Tableaux, séparateurs |
| Vert validation | `#16A34A` | Statuts OK |
| Orange attention | `#EA580C` | Statuts « à corriger » |
| Jaune information | `#FEF3C7` | Surlignages |

### 7.2   Typographie

- Police principale : **Inter** (sans-serif, moderne, libre de droits)
- Fallback : Calibri, Arial, sans-serif
- Tailles : 12px (légende), 14px (corps), 16px (titre carte), 24px (titre section), 32px (titre page)

### 7.3   Logos

- Logo VINCI Energies : à placer en haut à droite des pages de connexion et tableaux de bord, dans le footer général
- Logo Cegelec + VINCI Energies (composé) : sur les fiches tableau, étiquettes QR, en-têtes de DOE
- Fournis par l'utilisateur : `logo_vinci-removebg-preview.png` et `logo vinci Plus actemium fond blanc.png`

### 7.4   Composants UI

Utiliser **shadcn/ui** comme base de composants. C'est une bibliothèque de composants React copiée dans le projet (pas une dépendance), donc personnalisable au pixel près. Tous les composants suivants sont disponibles :

- Button (variants: default, destructive, outline, secondary, ghost, link)
- Input, Label, Textarea, Select, Checkbox, Radio
- Card, CardHeader, CardContent, CardFooter
- Dialog, AlertDialog, Sheet
- Tabs, TabsList, TabsContent
- Table, TableHeader, TableBody, TableRow, TableCell
- Toast, Alert
- Avatar, Badge, Separator
- DropdownMenu, ContextMenu
- Tooltip, Popover

### 7.5   Inspiration design

- Linear (https://linear.app) — sobriété, densité d'information, animations subtiles
- Notion — hiérarchie typographique, espacements
- Stripe Dashboard — tableaux denses lisibles, badges
- Vercel — minimalisme, contraste

À ne pas reproduire :
- Surcharge graphique (gradients, ombres marquées)
- Couleurs vives multiples
- Polices décoratives
- Icônes 3D ou illustrations cartoon

---

## 8. Modèle de données

13 entités principales. Détail des champs : voir cahier des charges, section 6.3.

```
┌──────────────┐
│   Project    │
└──────┬───────┘
       │ 1
       │
       │ N
┌──────▼─────────────────────────────────────────────┐
│   CanecoExport, Bordereau, CpsDocument             │
│   VerificationRun                                  │
│   Tableau                                          │
└────────────────────────────────────────────────────┘
       │
       │ N
┌──────▼──────┐
│   Departure │
└──────┬──────┘
       │ 1
       │
       │ N
┌──────▼─────────┐
│   FieldEntry   │
└────────────────┘

┌────────┐         ┌────────────┐         ┌──────────┐
│  User  │ N---N  │  Project   │ 1---N   │   Gap    │
└────────┘         └────────────┘         └──────────┘

┌──────────────────┐
│ TransferRequest  │
└──────────────────┘
```

---

## 9. Roadmap et état d'avancement

### 9.1   V1 — livrée (état au 12/07/2026)

Périmètre réalisé, validé en démonstration live devant les jurys VEAO et PFE, sur les cas pilotes DACHSER-L3 et NSK-L3.

- [x] Cartes d'empathie, problématisation, proposition de valeur
- [x] Cahier des charges fonctionnel et technique
- [x] Back-end FastAPI complet : auth JWT + 4 rôles (admin, BE, Chef de Chantier, RA), projects, imports CANECO / bordereau / CPS, vérifications, écarts, tableaux, saisies chantier, stock câbles, dashboard, métriques projet, route publique QR
- [x] Moteur de vérification déterministe : référentiel d'écarts **étendu de 10 à 20 codes (E-001 à E-020)** couvrant CANECO/bordereau, CANECO/CPS, CANECO/norme NF C 15-100 (règles en JSON), cohérence des protections (IB > In, IrTh, Icu) et complétude des données. Validation DACHSER indice B : 2 415 écarts détectés dont 2 bloquants E-004 confirmés manuellement
- [x] Front-end React : login, liste projets, page projet à onglets (Vue, Études, Bordereau, CPS, Vérifs, Carnet, Tableaux, Saisie, Stock, DOE, Paramètres), rapport d'écarts filtrable, mode présentation
- [x] Module A — Tableaux + QR : dérivation des tableaux depuis l'export CANECO, fiche publique par token, planches A4 de 8 étiquettes, fiche PDF
- [x] Carnet de câbles méthode CANECO : décomposition en conducteurs unipolaires, sommaire comparable au PDF officiel (DACHSER indice C : 41 616 m calculés vs 41 746 m CANECO, écart -0,31 %)
- [x] Module B — Saisie chantier : 1 saisie par ligne CANECO, longueur réelle + commentaire, commentaire obligatoire si longueur nulle ou écart > 50 %, indicateur d'écart coloré
- [x] Module B+ — Stock câbles : toutes les références du carnet, quantités achetée / livrée / utilisée (calculée depuis les saisies), seuils d'alerte configurables, filtres Type / Section / Âme / État
- [x] Module C — Tableau de bord multi-projets RA : KPI globaux, liste projets triable et filtrable, drill-down projet (alertes stock, écarts bloquants)
- [x] Permissions par rôle (le Chef de Chantier n'accède pas au dossier d'études), responsive mobile, accent charte VINCI
- [x] Données seed : 4 comptes de démonstration + projet DACHSER-L3
- [x] 238+ tests pytest verts, tests Vitest côté front

**Reste de la V1 initiale, reporté :**

- [ ] Génération DOE PDF + Excel (le service `services/doe` est créé mais vide ; les fiches tableau PDF unitaires existent déjà)
- [ ] Saisie photo en justification d'un écart (US-CC-03)
- [ ] Mode hors-ligne PWA avec synchronisation différée (US-CC-04 / US-CC-05)

### 9.2   V2 — prochaine étape (sous pilotage agence)

- Génération DOE complète (PDF + Excel, versionnée) — priorité 1, ferme la Brique 3
- Mode hors-ligne complet pour la PWA mobile (synchronisation différée)
- Photos en justification des écarts chantier
- Couche IA (API Claude) activée en production pour les bordereaux PDF non structurés (l'adapter `services/llm` existe, non branché en production)
- Module complet de transfert de matériel inter-projets
- Alertes par e-mail
- Comparaison de deux indices CANECO (A vs B)

### 9.3   V3 — 3 mois après

- Pilote sur 2 projets réels d'Actemium Cegelec (DACHSER déjà en cours, fin prévue 15/09/2026)
- Module de configuration des règles NF C 15-100 par l'admin (les règles sont déjà externalisées en JSON)
- Mode multi-utilisateurs simultanés sur un même projet (verrous optimistes)
- Statistiques agence (cumul sur tous les projets)

### 9.4   V4 — 6 mois après

- Déploiement sur l'agence pilote complète
- Documentation utilisateur PDF par persona
- Formation interne

### 9.5   Au-delà

- Réplication sur d'autres agences VINCI Energies BT
- Extension à d'autres lots techniques (chemins de câbles, gaines, courants faibles)

---

## 10. Risques et mesures

| Risque | Probabilité | Impact | Mesure |
|---|---|---|---|
| Hétérogénéité des bordereaux (PDF non structurés) | Élevée | Élevé | Couche IA optionnelle, format Excel privilégié pour V1 |
| Mauvaise qualité de connexion sur certains chantiers | Élevée | Moyen | Mode hors-ligne natif, synchronisation différée |
| Adoption faible par les Chefs de Chantier | Moyenne | Élevé | Saisie en 3 clics, formation courte, pilote sur volontaire |
| Évolution des règles normatives | Moyenne | Moyen | Module de configuration, pas de codage en dur |
| Confidentialité des données projet | Moyenne | Élevé | Authentification stricte, hébergement sous contrôle agence |
| Dépendance à un seul développeur | Élevée | Moyen | Documentation systématique, code commenté, conventions explicites |

---

## 11. Hors périmètre V1

- Intégration directe avec le SI achats VINCI
- Connexion automatique aux ERP des agences
- Module financier complet (devis, facturation, comptabilité analytique)
- Application mobile native (iOS/Android) — la PWA est jugée suffisante en V1
- Module de précâblage informatique (lot 700) — V2

---

## 12. Annexe — Tableau de mapping des écarts

Référentiel initial V1 (E-001 à E-010). L'implémentation l'a étendu à 20 codes (E-011 à E-020 : pouvoir de coupure Icu, réglages IrTh, sous-tableaux non appariés, règles CPS à vérifier, champs manquants, etc.) ; la liste exhaustive avec libellés exacts est dans `backend/app/services/verification/` et dans la documentation technique.

| Code | Libellé | Criticité | Source comparée |
|---|---|---|---|
| E-001 | Présent dans CANECO, absent du bordereau | Bloquant | CANECO ↔ Bordereau |
| E-002 | Présent dans le bordereau, absent de CANECO | Bloquant | CANECO ↔ Bordereau |
| E-003 | Écart de section entre CANECO et bordereau | Bloquant | CANECO ↔ Bordereau |
| E-004 | Écart de calibre de protection | Bloquant | CANECO ↔ Bordereau |
| E-005 | Écart de type de câble | À corriger | CANECO ↔ Bordereau |
| E-006 | Écart de longueur supérieur à 10 % | À signaler | CANECO ↔ Chantier |
| E-007 | Type de câble non conforme au CPS | Bloquant | CANECO ↔ CPS |
| E-008 | Section inférieure au minimum NF C 15-100 | Bloquant | CANECO ↔ Norme |
| E-009 | Chute de tension supérieure au seuil norme | Bloquant | CANECO ↔ Norme |
| E-010 | Suggestion de bonne pratique | Information | Heuristique |

---

**Fin du PRD V1**
