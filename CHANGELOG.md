# Changelog

## [Unreleased] — Initialisation du projet

### Module A — Tableaux electriques + QR codes (Brique 3)

- Derivation des tableaux electriques et de leurs departs depuis un export
  CANECO (regroupement par amont), idempotente : la regeneration conserve le
  `qr_token` des tableaux existants, les etiquettes deja posees restent valides.
- Generation de QR codes (correction d'erreur H, logo VINCI centre) calibres
  pour l'impression.
- Planche A4 d'etiquettes (8 par feuille, reperes de decoupe) prete a coller
  sur les armoires ; fiche tableau PDF (en-tete rouge VINCI).
- Route publique unique `GET /api/t/{token}` (+ `/fiche.pdf`) : fiche cables
  en lecture seule, sans authentification, rate-limitee, donnees minimales
  (ni code projet, ni client).
- Front : onglet « Tableaux » (generation, KPI, liste, modale QR, impression
  des etiquettes) et page publique mobile-first `/t/:token`.
- Aucune nouvelle dependance (qrcode, Pillow, reportlab deja presents).

### Carnet de cables — methode CANECO (refonte)

- Decomposition fidele a la methode du carnet CANECO BT v5.x : chaque ligne
  est eclatee en conducteurs unipolaires (cables ``nXm(1xS)`` ou cable principal
  + conducteurs Neutre / PE / PEN renseignes). Le sommaire est strictement
  comparable au PDF officiel CANECO.
- ``nb_cables_multi`` n'est plus applique aux cables paralleles (le ``n``
  exterieur de ``nXm(1xS)`` encode deja le compte) : corrige un double comptage.
- Nouvelle colonne ``Ame`` (Cuivre / Alu) dans le sommaire et l'API.
- Mesure DACHSER indice C : 41 616 m (CANECO PDF = 41 746 m, ecart -0,31 %).
  Reconnaissance des PE au format ``nX(1xS)`` (frequent sur cables paralleles),
  supprime un parasite ``1*2 mm²`` qui faisait perdre 200+ m.

### Module B — Saisie chantier (US-CC-02)

- Table ``field_entries`` (modele ``FieldEntry``) : 1 saisie par ligne CANECO,
  longueur reelle + commentaire optionnel. Migration alembic 010.
- Endpoints ``PUT/DELETE/GET /api/projects/{id}/field-entries[/{line_id}]``
  avec garde-fou : la ligne CANECO ciblee doit appartenir au projet.
- Acces ouvert au role CHEF_CHANTIER sur tous les projets actifs (gestion fine
  des assignations chantier renvoyee a V2). Aucun acces ecriture sur le
  dossier d'etudes (upload CANECO, bordereau, CPS) pour le Chef.
- Helper centralise ``app.api.access`` (lecture vs ecriture etudes) pour
  factoriser le controle d'acces, deduplique les ``_check_project_access``
  des routers concernes.
- Front : nouvel onglet « Saisie chantier », mobile-first, base sur le
  carnet par tableau du Module A. Champ numerique « Longueur reelle » + zone
  commentaire repliable. Indicateur d'ecart colore (vert <= 5 %, jaune 5-10 %,
  rouge > 10 %). KPI d'avancement.
- 7 nouveaux tests pytest (229/229 verts).
