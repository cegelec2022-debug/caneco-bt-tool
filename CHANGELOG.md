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

### Module B+ — Stock cables (auto-suivi)

- Modele ``CableStockItem`` + table ``cable_stock_items`` (migration 011) :
  une reference par (project, type_cable, section_label, ame), avec
  ``quantite_achetee`` (RA), ``quantite_livree`` (Chef) et ``seuil_alerte_min_m``.
- ``quantite_utilisee`` calculee en direct depuis les ``field_entries`` du
  projet, ventilee selon la decomposition CANECO (memes regles que le
  carnet de cables) : une saisie sur ``3X(1x150)`` 100 m alimente
  automatiquement la reference ``1*150 mm² Alu`` a hauteur de 300 m.
- Endpoints ``GET / PUT / DELETE /api/projects/{id}/cable-stock`` ; le seuil
  d'alerte est configurable par reference.
- Front : nouvel onglet « Stock cables » avec inputs editables (achete,
  livre, seuil), reste calcule, ligne ``ring`` rouge VINCI si en alerte,
  badge de notification sur l'onglet, tri (alertes en haut, sinon par
  section croissante). 9 nouveaux tests pytest (238/238 verts).

### Saisie chantier — regles metier

- Commentaire **obligatoire** quand la longueur reelle = 0 (circuit non tire)
  ou quand l'ecart absolu vs prevu depasse 50 %. Validation cote backend
  (422) et cote front (bouton bloque + message clair + champ commentaire
  ouvert automatiquement). Garantit la tracabilite pour le BE / RA.

### Permissions par role

- Le Chef de Chantier ne voit plus les onglets Bordereau / CPS / Verifications
  (reserves au dossier d'etudes BE / RA / admin). Onglet par defaut a
  l'ouverture d'un projet : Saisie chantier pour le Chef.
- Helper centralise ``app/api/access.py`` (lecture / ecriture etudes) pour
  factoriser le controle d'acces et separer proprement les permissions par
  role.

### Responsive mobile + accent rouge VINCI

- Layout : sidebar transformee en drawer (menu hamburger) sur mobile, fixe
  sur desktop (md+). Header adapte aux petits ecrans (titre raccourci,
  logo redimensionne).
- Barre d'onglets ProjectPage : scroll horizontal fluide sur mobile,
  scrollbar masquee (utilitaire ``.scrollbar-none``).
- Couleur rouge VINCI utilisee comme accent strategique (souligne d'onglet
  actif, bouton bloque pour commentaire manquant, badge d'alerte, alertes
  stock) tout en gardant le bleu VINCI comme couleur de structure.
