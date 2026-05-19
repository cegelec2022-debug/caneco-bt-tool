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
