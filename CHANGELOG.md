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
