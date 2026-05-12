"""Parser CPS (Cahier des Prescriptions Speciales) — extraction deterministe par regex V1.

Lit un PDF page par page via pdfplumber et applique des patterns pour extraire
les exigences techniques chiffrables. Concu pour etre dynamique sur n'importe
quel projet (DACHSER, NSK, ou autre) sans configuration specifique.

Chaque definition de pattern peut contenir :
  rule_type       : categorie semantique (pour le moteur de verification)
  context_label   : sous-contexte optionnel (eclairage, prises, moteur...)
  pattern         : re.Pattern
  value_group     : index de groupe capturant la valeur (0 = match entier)
  fixed_value     : si defini, utilise cette valeur fixe au lieu du groupe extrait
  strip_spaces    : True (defaut) → supprime espaces (types cable) ; False → preserve
  unit            : unite affichee (ou None)
  confidence      : float entre 0 et 1
  desc_template   : f-string pour la description lisible

Architecture extensible : extract_rules(use_llm=False).
En V2, use_llm=True deleguera a LlmAdapter.extract_cps_rules(pdf_path).
"""

import re
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Definitions des patterns
# ---------------------------------------------------------------------------

_RULE_PATTERNS: list[dict[str, Any]] = [

    # =========================================================================
    # TENSION NOMINALE RESEAU
    # (comparaison CANECO colonne Un)
    # =========================================================================
    {
        "rule_type": "tension_nominale",
        "context_label": None,
        "pattern": re.compile(
            r"tension[s]?\s+(?:nominale?s?|d'alimentation|r[eé]seau)[^\n.]{0,80}?"
            r"(\d{2,3})\s*[Vv]\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "V",
        "confidence": 0.9,
        "desc_template": "Tension nominale du reseau : {value} V",
    },
    {
        "rule_type": "tension_nominale",
        "context_label": "distribution",
        "pattern": re.compile(
            r"(\d{2,3})\s*[Vv]\s*/\s*(\d{3})\s*[Vv]\b",
            re.IGNORECASE,
        ),
        "value_group": 2,
        "strip_spaces": False,
        "unit": "V",
        "confidence": 0.85,
        "desc_template": "Tension de distribution : {value} V",
    },
    {
        "rule_type": "tension_nominale",
        "context_label": "triphasee",
        "pattern": re.compile(
            r"\b(400|690)\s*[Vv]\b[^\n.]{0,60}?"
            r"(?:triphas[eé]|trois\s+phases?|3\s*[Pp]h|HTA|BTA)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "V",
        "confidence": 0.9,
        "desc_template": "Tension nominale triphasee : {value} V",
    },

    # =========================================================================
    # FREQUENCE RESEAU
    # =========================================================================
    {
        "rule_type": "frequence_reseau",
        "context_label": None,
        "pattern": re.compile(
            r"fr[eé]quence[^\n.]{0,50}?(\d{2})\s*[Hh]z",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "Hz",
        "confidence": 0.9,
        "desc_template": "Frequence du reseau : {value} Hz",
    },
    {
        "rule_type": "frequence_reseau",
        "context_label": None,
        "pattern": re.compile(
            r"(\d{2})\s*[Hh]z[^\n.]{0,30}?(?:fr[eé]quence|r[eé]seau|secteur|EDF)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "Hz",
        "confidence": 0.85,
        "desc_template": "Frequence du reseau : {value} Hz",
    },

    # =========================================================================
    # COURANT DE COURT-CIRCUIT ICC
    # (comparaison CANECO colonne Icc)
    # =========================================================================
    {
        "rule_type": "courant_court_circuit",
        "context_label": None,
        "pattern": re.compile(
            r"\bIcc\s*[=:≥>]\s*(\d+(?:[.,]\d+)?)\s*kA",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "kA",
        "confidence": 0.95,
        "desc_template": "Courant de court-circuit Icc : {value} kA",
    },
    {
        "rule_type": "courant_court_circuit",
        "context_label": None,
        "pattern": re.compile(
            r"courant\s+de\s+court[- ]circuit[^\n.]{0,80}?(\d+(?:[.,]\d+)?)\s*kA",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "kA",
        "confidence": 0.9,
        "desc_template": "Courant de court-circuit : {value} kA",
    },
    {
        "rule_type": "courant_court_circuit",
        "context_label": None,
        "pattern": re.compile(
            r"(\d+(?:[.,]\d+)?)\s*kA[^\n.]{0,50}?(?:Icc|court[- ]circuit|coupure)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "kA",
        "confidence": 0.8,
        "desc_template": "Courant de court-circuit : {value} kA",
    },

    # =========================================================================
    # POUVOIR DE COUPURE (Icu / Ics)
    # (comparaison CANECO colonne Pdc)
    # =========================================================================
    {
        "rule_type": "pouvoir_coupure",
        "context_label": None,
        "pattern": re.compile(
            r"\b(?:Icu|Ics|pouvoir\s+de\s+coupure\s+ultime)\s*[=:≥>]\s*(\d+(?:[.,]\d+)?)\s*kA",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "kA",
        "confidence": 0.95,
        "desc_template": "Pouvoir de coupure Icu >= {value} kA",
    },
    {
        "rule_type": "pouvoir_coupure",
        "context_label": None,
        "pattern": re.compile(
            r"pouvoir\s+de\s+coupure[^\n.]{0,80}?(\d+(?:[.,]\d+)?)\s*kA",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "kA",
        "confidence": 0.9,
        "desc_template": "Pouvoir de coupure : {value} kA",
    },

    # =========================================================================
    # SECTIONS MINIMALES CONDUCTEURS
    # (comparaison directe colonne CANECO Section)
    # =========================================================================
    {
        "rule_type": "section_minimale",
        "context_label": None,
        "pattern": re.compile(
            r"section\s*(?:minimale?s?|mini(?:mum)?)[^\n.]{0,80}?(\d+[,.]?\d*)\s*mm[²2]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mm²",
        "confidence": 0.9,
        "desc_template": "Section minimale : {value} mm²",
    },
    {
        "rule_type": "section_minimale",
        "context_label": "eclairage",
        "pattern": re.compile(
            r"[eé]clairage[^\n.]{0,80}?(\d+[,.]?\d*)\s*mm[²2]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mm²",
        "confidence": 0.85,
        "desc_template": "Section minimale eclairage : {value} mm²",
    },
    {
        "rule_type": "section_minimale",
        "context_label": "prises",
        "pattern": re.compile(
            r"prises?[^\n.]{0,80}?(\d+[,.]?\d*)\s*mm[²2]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mm²",
        "confidence": 0.85,
        "desc_template": "Section minimale prises courant : {value} mm²",
    },
    {
        "rule_type": "section_minimale",
        "context_label": "moteur",
        "pattern": re.compile(
            r"moteurs?[^\n.]{0,80}?(\d+[,.]?\d*)\s*mm[²2]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mm²",
        "confidence": 0.8,
        "desc_template": "Section minimale moteur : {value} mm²",
    },

    # =========================================================================
    # CONDUCTEUR NEUTRE
    # =========================================================================
    {
        "rule_type": "section_neutre",
        "context_label": None,
        "pattern": re.compile(
            r"(?:conducteur\s+)?neutre[^\n.]{0,80}?(\d+[,.]?\d*)\s*mm[²2]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mm²",
        "confidence": 0.85,
        "desc_template": "Section neutre : {value} mm²",
    },
    {
        "rule_type": "section_neutre",
        "context_label": "reduit",
        "pattern": re.compile(
            r"(?:neutre\s+r[eé]duit|section\s+r[eé]duite\s+(?:du\s+)?neutre|50\s*%[^\n.]{0,40}?neutre)",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Reduit (50%)",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Neutre a section reduite (50 % de la phase) admis",
    },

    # =========================================================================
    # CONDUCTEUR DE PROTECTION PE
    # =========================================================================
    {
        "rule_type": "section_pe",
        "context_label": None,
        "pattern": re.compile(
            r"(?:conducteur\s+de\s+)?(?:protection\s+)?(?:PE|PEN)\s*[=:≥>]\s*(\d+[,.]?\d*)\s*mm[²2]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mm²",
        "confidence": 0.85,
        "desc_template": "Section PE/PEN requise : {value} mm²",
    },

    # =========================================================================
    # CHUTE DE TENSION
    # (comparaison CANECO DeltaU)
    # =========================================================================
    {
        "rule_type": "chute_tension_max",
        "context_label": None,
        "pattern": re.compile(
            r"chute\s+de\s+tension[^\n.]{0,80}?(\d+[,.]?\d*)\s*%",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "%",
        "confidence": 0.9,
        "desc_template": "Chute de tension maximale : {value} %",
    },
    {
        "rule_type": "chute_tension_max",
        "context_label": "eclairage",
        "pattern": re.compile(
            r"[eé]clairage[^\n.]{0,60}?(\d+[,.]?\d*)\s*%[^\n.]{0,40}?(?:chute|tension)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "%",
        "confidence": 0.8,
        "desc_template": "Chute de tension eclairage : {value} %",
    },
    {
        "rule_type": "chute_tension_max",
        "context_label": "force",
        "pattern": re.compile(
            r"d[eé]parts?\s+(?:moteur|force)[^\n.]{0,60}?(\d+[,.]?\d*)\s*%[^\n.]{0,40}?(?:chute|tension)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "%",
        "confidence": 0.8,
        "desc_template": "Chute de tension depart force/moteur : {value} %",
    },

    # =========================================================================
    # TYPES DE CABLES
    # (comparaison CANECO TypeCable)
    # =========================================================================
    {
        "rule_type": "type_cable_requis",
        "context_label": None,
        "pattern": re.compile(
            r"\b(U1000\s*A?R\s*O?2V|U\s*1000\s*A?R\s*O?2V)\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Type de cable requis : {value}",
    },
    {
        "rule_type": "type_cable_requis",
        "context_label": None,
        "pattern": re.compile(
            r"\b(RO2V|R02V)\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Type de cable requis : {value}",
    },
    {
        "rule_type": "type_cable_requis",
        "context_label": None,
        "pattern": re.compile(
            r"\b(CR1|FR-N1X1|H07[VRU][RN]?-?[FKR]?|H05[VRU][VR]-?[F]?)\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Type de cable requis : {value}",
    },
    {
        "rule_type": "type_cable_requis",
        "context_label": "lsoh",
        "pattern": re.compile(
            r"(?:faible\s+[eé]mission\s+de\s+fum[eé]e|sans\s+halog[eè]ne|LSOH|LSZH|HF[^\w])",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "LSOH/HF",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Cable a faible emission de fumee sans halogene (LSOH/HF) requis",
    },

    # =========================================================================
    # TENSION D'ISOLEMENT DU CABLE (600/1000V, 450/750V...)
    # =========================================================================
    {
        "rule_type": "tension_isolement",
        "context_label": None,
        "pattern": re.compile(
            r"\b(\d{3,4})\s*[Vv]\s*/\s*(\d{3,4})\s*[Vv]\b[^\n.]{0,50}?"
            r"(?:c[aâ]ble|conducteur|isolement|tension)",
            re.IGNORECASE,
        ),
        "value_group": 2,
        "strip_spaces": False,
        "unit": "V",
        "confidence": 0.85,
        "desc_template": "Tension d'isolement cable : {value} V",
    },
    {
        "rule_type": "tension_isolement",
        "context_label": None,
        "pattern": re.compile(
            r"tensions?\s+d'isolement[^\n.]{0,80}?(\d{3,4})\s*[Vv]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "V",
        "confidence": 0.85,
        "desc_template": "Tension d'isolement minimale : {value} V",
    },

    # =========================================================================
    # CABLES RESISTANTS AU FEU
    # =========================================================================
    {
        "rule_type": "cable_resistance_feu",
        "context_label": None,
        "pattern": re.compile(
            r"c[aâ]bles?\s+[^\n.]{0,50}?(CR1|FR-N1X1)[^\n.]{0,50}?"
            r"(?:r[eé]sistants?\s+au\s+feu|circuit\s+de\s+s[eé]curit[eé]|d[eé]senfumage)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Cable resistant au feu type {value} requis",
    },
    {
        "rule_type": "cable_resistance_feu",
        "context_label": None,
        "pattern": re.compile(
            r"(?:CR1|FR-N1X1)[^\n.]{0,60}?"
            r"(?:r[eé]sistants?\s+au\s+feu|s[eé]curit[eé]\s+incendie|d[eé]senfumage)",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "CR1",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Cable CR1 pour circuit de securite incendie requis",
    },
    {
        "rule_type": "cable_resistance_feu",
        "context_label": "general",
        "pattern": re.compile(
            r"c[aâ]bles?\s+r[eé]sistants?\s+au\s+feu",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Requis",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Cable resistant au feu requis (type a preciser dans extrait)",
    },

    # =========================================================================
    # CABLE BLINDE
    # =========================================================================
    {
        "rule_type": "cable_blinde",
        "context_label": None,
        "pattern": re.compile(
            r"c[aâ]bles?\s+blind[eé]s?|liaison\s+blind[eé]e?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Requis",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Cable blinde requis (perturbations electromagnetiques)",
    },

    # =========================================================================
    # DDR (dispositifs differentiels residuels)
    # (comparaison CANECO colonne DDR_sensib)
    # =========================================================================
    {
        "rule_type": "ddr_sensibilite",
        "context_label": None,
        "pattern": re.compile(
            r"(?:DDR|diff[eé]rentiel[les]*)[^\n.]{0,80}?(\d+)\s*mA",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mA",
        "confidence": 0.9,
        "desc_template": "DDR de sensibilite {value} mA",
    },
    {
        "rule_type": "ddr_sensibilite",
        "context_label": None,
        "pattern": re.compile(
            r"sensibilit[eé][^\n.]{0,40}?(\d+)\s*mA",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mA",
        "confidence": 0.9,
        "desc_template": "DDR de sensibilite {value} mA",
    },
    {
        "rule_type": "ddr_sensibilite",
        "context_label": None,
        "pattern": re.compile(
            r"(\d+)\s*mA\s+(?:de\s+)?(?:sensibilit[eé]|r[eé]siduel)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "mA",
        "confidence": 0.9,
        "desc_template": "DDR de sensibilite {value} mA",
    },
    {
        "rule_type": "ddr_type",
        "context_label": None,
        "pattern": re.compile(
            r"(?:DDR|diff[eé]rentiel|interrupteur\s+diff[eé]rentiel)[^\n.]{0,50}?"
            r"type\s+([A-Fa-f]{1,2})\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "DDR de type {value}",
    },

    # =========================================================================
    # COURBE DE DECLENCHEMENT DISJONCTEUR
    # (comparaison CANECO colonne Courbe)
    # =========================================================================
    {
        "rule_type": "courbe_disjoncteur",
        "context_label": None,
        "pattern": re.compile(
            r"courbe\s+(?:de\s+(?:d[eé]clenchement|r[eé]ponse|d[eé]clench))[^\n.]{0,60}?"
            r"\b([BCDGMA]{1,2})\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Courbe de declenchement disjoncteur : {value}",
    },
    {
        "rule_type": "courbe_disjoncteur",
        "context_label": None,
        "pattern": re.compile(
            r"disjoncteurs?[^\n.]{0,60}?courbe\s+([BCDGMA]{1,2})\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Courbe de declenchement disjoncteur : {value}",
    },
    {
        "rule_type": "courbe_disjoncteur",
        "context_label": None,
        "pattern": re.compile(
            r"\bcourbes?\s+([BCDGMA]{1,2})\b[^\n.]{0,50}?disjoncteur",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Courbe de declenchement disjoncteur : {value}",
    },
    {
        "rule_type": "courbe_disjoncteur",
        "context_label": "moteur",
        "pattern": re.compile(
            r"(?:d[eé]part\s+)?moteur[^\n.]{0,60}?"
            r"(?:courbe\s+)?(?:MA|AM)\b",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "MA",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Courbe MA (magnetique pur) pour departs moteur",
    },

    # =========================================================================
    # CALIBRE PROTECTION
    # (comparaison CANECO colonne Calibre)
    # =========================================================================
    {
        "rule_type": "calibre_protection",
        "context_label": "minimum",
        "pattern": re.compile(
            r"calibre\s+(?:minimum|min(?:imum)?)[^\n.]{0,60}?(\d+(?:[.,]\d+)?)\s*[Aa]\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "A",
        "confidence": 0.85,
        "desc_template": "Calibre minimum protection : {value} A",
    },
    {
        "rule_type": "calibre_protection",
        "context_label": "maximum",
        "pattern": re.compile(
            r"calibre\s+(?:maximum|max(?:imum)?)[^\n.]{0,60}?(\d+(?:[.,]\d+)?)\s*[Aa]\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "A",
        "confidence": 0.85,
        "desc_template": "Calibre maximum protection : {value} A",
    },
    {
        "rule_type": "calibre_protection",
        "context_label": "interrupteur_general",
        "pattern": re.compile(
            r"(?:interrupteur|disjoncteur)\s+g[eé]n[eé]ral[^\n.]{0,80}?(\d+(?:[.,]\d+)?)\s*[Aa]\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "A",
        "confidence": 0.85,
        "desc_template": "Calibre interrupteur/disjoncteur general : {value} A",
    },

    # =========================================================================
    # DISJONCTEURS
    # =========================================================================
    {
        "rule_type": "disjoncteur_kind",
        "context_label": "debrochable",
        "pattern": re.compile(
            r"disjoncteurs?\s+d[eé]brochables?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Debrochable",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Disjoncteur debrochable requis",
    },
    {
        "rule_type": "disjoncteur_kind",
        "context_label": "magnetique",
        "pattern": re.compile(
            r"disjoncteurs?\s+(?:purement\s+)?magn[eé]tiques?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Magnetique",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Disjoncteur purement magnetique requis",
    },
    {
        "rule_type": "disjoncteur_kind",
        "context_label": "moteur",
        "pattern": re.compile(
            r"disjoncteurs?\s+(?:de\s+)?(?:protection\s+)?moteurs?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Disjoncteur-moteur",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Disjoncteur moteur requis pour departs moteur",
    },

    # =========================================================================
    # SELECTIVITE
    # (comparaison CANECO schema selectivite)
    # =========================================================================
    {
        "rule_type": "selectivite",
        "context_label": None,
        "pattern": re.compile(
            r"s[eé]lectivit[eé][^\n.]{0,80}?"
            r"(totale|partielle|chronom[eé]trique|amp[eè]rem[eé]trique|verticale|horizontale)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Selectivite {value} requise",
    },

    # =========================================================================
    # SCHEMA DE LIAISON A LA TERRE
    # (comparaison CANECO schema TN-S/TT/IT)
    # =========================================================================
    {
        "rule_type": "schema_mise_terre",
        "context_label": None,
        "pattern": re.compile(
            r"\b(TN-?S|TN-?C(?:-S)?|TT|IT)\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Schema de liaison a la terre : {value}",
    },

    # =========================================================================
    # PRISE DE TERRE (resistance)
    # =========================================================================
    {
        "rule_type": "prise_terre",
        "context_label": None,
        "pattern": re.compile(
            r"r[eé]sistance\s+(?:de\s+(?:la\s+)?)?(?:prise\s+de\s+terre|terre|boucle)[^\n.]{0,60}?"
            r"(?:[<=≤<]{1,2})\s*(\d+(?:[.,]\d+)?)\s*[Ωo]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "Ω",
        "confidence": 0.9,
        "desc_template": "Resistance de la prise de terre <= {value} Ohm",
    },
    {
        "rule_type": "prise_terre",
        "context_label": None,
        "pattern": re.compile(
            r"(?:prise\s+de\s+terre|piquet\s+(?:de\s+)?terre)[^\n.]{0,80}?"
            r"(\d+(?:[.,]\d+)?)\s*[Ωo]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "Ω",
        "confidence": 0.85,
        "desc_template": "Resistance prise de terre : {value} Ohm",
    },

    # =========================================================================
    # LIAISONS EQUIPOTENTIELLES
    # =========================================================================
    {
        "rule_type": "liaison_equipotentielle",
        "context_label": None,
        "pattern": re.compile(
            r"liaisons?\s+[eé]quipotentielle?s?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Requise",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Liaison equipotentielle requise",
    },

    # =========================================================================
    # MODE DE POSE DES CABLES
    # (comparaison CANECO colonne ModePose)
    # =========================================================================
    {
        "rule_type": "mode_pose_cable",
        "context_label": "chemin_cables",
        "pattern": re.compile(
            r"chemin(?:s?)\s+de\s+c[aâ]bles?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Chemin de cables",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Pose sur chemin de cables",
    },
    {
        "rule_type": "mode_pose_cable",
        "context_label": "conduit",
        "pattern": re.compile(
            r"(?:sous|en)\s+(?:conduits?|tubes?|fourreaux?)"
            r"[^\n.]{0,40}?(?:PVC|PEHD|ICT|IRL|IRO|ICA|M25|M32|M40)?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Sous conduit",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Pose sous conduit/tube protecteur",
    },
    {
        "rule_type": "mode_pose_cable",
        "context_label": "apparent",
        "pattern": re.compile(
            r"pose\s+(?:en\s+)?apparent[e]?[^\n.]{0,40}?c[aâ]bles?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Apparent",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Pose apparente des cables",
    },
    {
        "rule_type": "mode_pose_cable",
        "context_label": "prefabrique",
        "pattern": re.compile(
            r"canalisations?\s+pr[eé]fabriqu[eé]es?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Canalisation prefabriquee",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Canalisation electrique prefabriquee",
    },

    # =========================================================================
    # CANALISATIONS ENTERREES
    # =========================================================================
    {
        "rule_type": "canalisation_enterree",
        "context_label": "profondeur",
        "pattern": re.compile(
            r"(?:profondeur\s+(?:de\s+)?pose|pose\s+[eé]nterr[eé]e?)[^\n.]{0,60}?(\d+)\s*(?:cm|m\b)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "cm",
        "confidence": 0.8,
        "desc_template": "Profondeur de pose enterree : {value} cm",
    },
    {
        "rule_type": "canalisation_enterree",
        "context_label": "grillage",
        "pattern": re.compile(
            r"grillage\s+avertisseur",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Requis",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Grillage avertisseur pour canalisations enterrees requis",
    },

    # =========================================================================
    # MARQUAGE / ETIQUETAGE DES CABLES
    # =========================================================================
    {
        "rule_type": "marquage_cable",
        "context_label": None,
        "pattern": re.compile(
            r"(?:rep[eé]rage|[eé]tiquetage)[^\n.]{0,80}?"
            r"(?:c[aâ]bles?|circuits?|d[eé]parts?|conducteurs?)",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Requis",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Reperage/etiquetage des cables et circuits requis",
    },
    {
        "rule_type": "marquage_cable",
        "context_label": "gravure",
        "pattern": re.compile(
            r"(?:[eé]tiquettes?\s+(?:de\s+)?(?:rep[eé]rage|identification)|grav[eé]|gravure)",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Etiquette gravee",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Etiquettes de reperage gravees exigees",
    },

    # =========================================================================
    # ALIMENTATION SECOURUE (ASI / UPS / AGAM)
    # =========================================================================
    {
        "rule_type": "alimentation_secourue",
        "context_label": None,
        "pattern": re.compile(
            r"\b(ASI|UPS|AGAM|onduleur)\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Alimentation secouree : {value}",
    },
    {
        "rule_type": "alimentation_secourue",
        "context_label": "general",
        "pattern": re.compile(
            r"alimentation\s+secour[ue]e?",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Secourue",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Alimentation secouree requise (voir extrait)",
    },

    # =========================================================================
    # AUTONOMIE ALIMENTATION SECOURS
    # =========================================================================
    {
        "rule_type": "autonomie_secours",
        "context_label": None,
        "pattern": re.compile(
            r"autonomie[^\n.]{0,80}?(\d+(?:[.,]\d+)?)\s*(?:heure?s?|h\b)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "h",
        "confidence": 0.85,
        "desc_template": "Autonomie alimentation secours : {value} h",
    },
    {
        "rule_type": "autonomie_secours",
        "context_label": None,
        "pattern": re.compile(
            r"autonomie[^\n.]{0,80}?(\d+)\s*(?:minutes?|min\b)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "min",
        "confidence": 0.85,
        "desc_template": "Autonomie alimentation secours : {value} min",
    },
    {
        "rule_type": "autonomie_secours",
        "context_label": None,
        "pattern": re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:heure?s?|h\b)\s+d'autonomie",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "h",
        "confidence": 0.85,
        "desc_template": "Autonomie alimentation secours : {value} h",
    },

    # =========================================================================
    # PROTECTIONS SURTENSION
    # =========================================================================
    {
        "rule_type": "protection_surtension",
        "context_label": "parafoudre",
        "pattern": re.compile(
            r"\bparafoudres?\b",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Parafoudre",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.75,
        "desc_template": "Protection parafoudre mentionnee",
    },
    {
        "rule_type": "protection_surtension",
        "context_label": "paratonnerre",
        "pattern": re.compile(
            r"\bparatonnerres?\b",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Paratonnerre",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.75,
        "desc_template": "Protection paratonnerre mentionnee",
    },

    # =========================================================================
    # INDICES DE PROTECTION IP / IK
    # (comparaison CANECO colonnes IP, IK)
    # =========================================================================
    {
        "rule_type": "indice_protection",
        "context_label": None,
        "pattern": re.compile(
            r"\bIP\s*(\d{2,3})\b",
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.9,
        "desc_template": "Indice de protection IP{value} requis",
    },
    {
        "rule_type": "indice_choc",
        "context_label": None,
        "pattern": re.compile(
            r"\bIK\s*0?(\d{2})\b",
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Resistance aux chocs IK{value} requis",
    },

    # =========================================================================
    # RESISTANCE D'ISOLEMENT
    # =========================================================================
    {
        "rule_type": "resistance_isolement",
        "context_label": None,
        "pattern": re.compile(
            r"r[eé]sistance\s+d.[i]?solement[^\n.]{0,60}?(\d+(?:[.,]\d+)?)\s*M[Ωo]",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "MΩ",
        "confidence": 0.85,
        "desc_template": "Resistance d'isolement minimale : {value} MΩ",
    },
    {
        "rule_type": "resistance_isolement",
        "context_label": None,
        "pattern": re.compile(
            r"(\d+(?:[.,]\d+)?)\s*M[Ωo][^\n.]{0,30}?(?:isolement|isolation)",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "MΩ",
        "confidence": 0.8,
        "desc_template": "Resistance d'isolement : {value} MΩ",
    },

    # =========================================================================
    # CLASSE D'ISOLATION
    # =========================================================================
    {
        "rule_type": "classe_isolation",
        "context_label": None,
        "pattern": re.compile(
            r"\bclasse\s+(I{1,2})\b(?:[^\n.]{0,30}?(?:protection|[eé]lectrique|isolation))?",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Classe d'isolation materiel : Classe {value}",
    },

    # =========================================================================
    # SECURITE INCENDIE / DESENFUMAGE
    # =========================================================================
    {
        "rule_type": "securite_incendie",
        "context_label": "desenfumage",
        "pattern": re.compile(
            r"\bd[eé]senfumages?\b",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "Desenfumage",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Equipement de desenfumage mentionne",
    },
    {
        "rule_type": "securite_incendie",
        "context_label": "ssi",
        "pattern": re.compile(
            r"\b(?:SSI|systeme\s+de\s+s[eé]curit[eé]\s+incendie)\b",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "SSI",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Systeme de securite incendie (SSI) mentionne",
    },
    {
        "rule_type": "securite_incendie",
        "context_label": "das",
        "pattern": re.compile(
            r"\b(?:DAS|dispositif\s+actionn[eé]\s+de\s+s[eé]curit[eé])\b",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "DAS",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "Dispositif Actionne de Securite (DAS) mentionne",
    },

    # =========================================================================
    # CONDITIONS ENVIRONNEMENTALES
    # =========================================================================
    {
        "rule_type": "condition_environnementale",
        "context_label": "temperature",
        "pattern": re.compile(
            r"temp[eé]rature[^\n.]{0,80}?(-?\d+)\s*°?\s*C\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "°C",
        "confidence": 0.8,
        "desc_template": "Condition de temperature : {value} °C",
    },
    {
        "rule_type": "condition_environnementale",
        "context_label": "humidite",
        "pattern": re.compile(
            r"humidit[eé][^\n.]{0,50}?(\d+)\s*%",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "%",
        "confidence": 0.75,
        "desc_template": "Condition d'humidite : {value} %",
    },
    {
        "rule_type": "condition_environnementale",
        "context_label": "altitude",
        "pattern": re.compile(
            r"altitude[^\n.]{0,50}?(\d+)\s*m\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": "m",
        "confidence": 0.75,
        "desc_template": "Altitude d'installation : {value} m",
    },

    # =========================================================================
    # MARQUES IMPOSEES
    # =========================================================================
    {
        "rule_type": "marque_imposee",
        "context_label": None,
        "pattern": re.compile(
            r"\b(Schneider\s+Electric|Schneider|Legrand|ABB|Siemens|Hager|Socomec|Merlin\s+Gerin|Telemecanique)\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.7,
        "desc_template": "Marque imposee ou preconisee : {value}",
    },
]


# ---------------------------------------------------------------------------
# Resultat
# ---------------------------------------------------------------------------


class CpsParseResult:
    """Resultat du parsing d'un CPS PDF."""

    def __init__(self) -> None:
        self.rules: list[dict[str, Any]] = []
        self.page_count: int = 0


# ---------------------------------------------------------------------------
# Point d'entree public
# ---------------------------------------------------------------------------


def extract_rules(file_path: Path, use_llm: bool = False) -> CpsParseResult:
    """Extrait les regles techniques d'un CPS PDF.

    Args:
        file_path: Chemin absolu vers le fichier PDF.
        use_llm: Desactive en V1. Si True (V2), delegue a LlmAdapter.

    Returns:
        CpsParseResult avec la liste des regles extraites.

    Raises:
        ValueError: Si le fichier est vide ou illisible.
        ImportError: Si pdfplumber n'est pas installe.
    """
    if use_llm:
        logger.warning("use_llm=True ignore en V1 (LlmAdapter desactive). Fallback regex.")

    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "pdfplumber est requis pour le parser CPS. pip install pdfplumber"
        ) from exc

    logger.info(f"Parsing CPS : {file_path}")
    result = CpsParseResult()

    with pdfplumber.open(str(file_path)) as pdf:
        result.page_count = len(pdf.pages)
        if result.page_count == 0:
            raise ValueError("Le PDF est vide ou illisible.")

        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            _extract_from_page(text, page_num, result)

    logger.info(
        f"CPS parse : {result.page_count} pages, {len(result.rules)} regles extraites"
    )
    return result


# ---------------------------------------------------------------------------
# Extraction par page
# ---------------------------------------------------------------------------


def _extract_from_page(text: str, page_num: int, result: CpsParseResult) -> None:
    """Applique tous les patterns sur le texte d'une page et enrichit result."""
    for rule_def in _RULE_PATTERNS:
        for match in rule_def["pattern"].finditer(text):

            # Valeur : fixed_value > group extrait
            if "fixed_value" in rule_def:
                value = rule_def["fixed_value"]
            else:
                group_idx: int = rule_def["value_group"]
                raw = match.group(0) if group_idx == 0 else match.group(group_idx)
                strip = rule_def.get("strip_spaces", True)
                value = _normalize_value(raw, strip_spaces=strip)

            context_label = rule_def.get("context_label")

            if _already_present(result.rules, rule_def["rule_type"], value, context_label):
                continue

            source_excerpt = _extract_context(text, match.start(), radius=220)
            description = rule_def["desc_template"].format(value=value)

            result.rules.append(
                {
                    "rule_type": rule_def["rule_type"],
                    "value": value,
                    "unit": rule_def.get("unit"),
                    "context_label": context_label,
                    "description": description,
                    "source_page": page_num,
                    "source_excerpt": source_excerpt,
                    "confidence": rule_def["confidence"],
                    "requires_validation": True,
                }
            )


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _normalize_value(raw: str, strip_spaces: bool = True) -> str:
    """Normalise une valeur extraite.

    Args:
        raw: Chaine brute extraite par le regex.
        strip_spaces: Si True, supprime les espaces (adapte aux types cable).
                      Si False, garde les espaces et met juste en majuscules.
    """
    v = raw.strip().replace(",", ".")
    if strip_spaces:
        v = re.sub(r"\s+", "", v).upper()
    else:
        v = re.sub(r"\s+", " ", v).upper()
    return v


def _already_present(
    rules: list[dict],
    rule_type: str,
    value: str,
    context_label: str | None,
) -> bool:
    """Evite les doublons exacts (meme type + valeur + contexte)."""
    return any(
        r["rule_type"] == rule_type
        and r["value"] == value
        and r.get("context_label") == context_label
        for r in rules
    )


def _extract_context(text: str, pos: int, radius: int = 220) -> str:
    """Extrait un extrait de texte autour d'une position pour traçabilite."""
    start = max(0, pos - radius // 2)
    end = min(len(text), pos + radius)
    snippet = text[start:end].strip()
    return re.sub(r"\s+", " ", snippet)
