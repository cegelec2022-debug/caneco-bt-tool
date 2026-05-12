"""Parser CPS (Cahier des Prescriptions Speciales) — extraction deterministe par regex V1.

Lit un PDF page par page via pdfplumber et applique des patterns pour extraire
les exigences techniques chiffrables. Concu pour etre dynamique sur n'importe
quel projet (DACHSER, NSK, ou autre) sans configuration specifique.

Chaque definition de pattern peut contenir :
  rule_type       : categorie semantique (pour le moteur de verification)
  context_label   : sous-contexte optionnel (eclairage, prises, debrochable...)
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
    # SECTIONS MINIMALES
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

    # =========================================================================
    # TYPES DE CABLES (valeur = type normalise, espaces supprimes)
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
            r"\b(CR1|FR-N1X1|H07[VRU][RN]?-?[FKR]?|LSOH|LSZH|HF)\b",
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
            r"(?:faible\s+[eé]mission\s+de\s+fum[eé]e|sans\s+halog[eè]ne)",
            re.IGNORECASE,
        ),
        "value_group": 0,
        "fixed_value": "LSOH/HF",
        "strip_spaces": False,
        "unit": None,
        "confidence": 0.8,
        "desc_template": "Cable a faible emission de fumee (LSOH/HF) requis",
    },

    # =========================================================================
    # CABLES RESISTANTS AU FEU
    # Probleme precedent : on capturait la phrase entiere → valeur illisible.
    # Correction : deux patterns specifiques avec fixed_value ou capture cible.
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
    # DDR (dispositifs differentiels residuels)
    # Trois formulations courantes dans les CPS francais :
    #   "DDR ... 30 mA"
    #   "differentiel(les) ... sensibilite ... 30 mA"
    #   "30 mA de sensibilite"
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
            r"(?:DDR|diff[eé]rentiel)[^\n.]{0,40}?type\s+([AaCcBb]{1,2})\b",
            re.IGNORECASE,
        ),
        "value_group": 1,
        "strip_spaces": True,
        "unit": None,
        "confidence": 0.85,
        "desc_template": "DDR de type {value}",
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

    # =========================================================================
    # SCHEMA DE MISE A LA TERRE
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
        "desc_template": "Alimentation secourue : {value}",
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
            r"temp[eé]rature[^\n.]{0,60}?(-?\d+)\s*°?\s*C\b",
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
    # SELECTIVITE
    # =========================================================================
    {
        "rule_type": "selectivite",
        "context_label": None,
        "pattern": re.compile(
            r"s[eé]lectivit[eé][^\n.]{0,60}?"
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
    # MARQUES IMPOSEES (strip_spaces=False pour garder les espaces lisibles)
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
