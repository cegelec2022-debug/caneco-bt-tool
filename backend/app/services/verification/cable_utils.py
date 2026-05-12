"""Utilitaires de parsing des designations de cables CANECO et bordereau."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Parsing designation cable CANECO BT
#
# Formats simples :
#   "5G6"        -> section=6.0 mm²  (5 conducteurs avec PE)
#   "4G2.5"      -> section=2.5 mm²
#   "3x95+T50"   -> section=95.0 mm²
#   "1x240"      -> section=240.0 mm²
#   "2G1.5"      -> section=1.5 mm²
#
# Formats multi-câbles unipolaires (CANECO grandes puissances) :
#   "3X(1x35)"        -> 3 câbles unipolaires de 35 mm²  -> section=35
#   "4X(1x300)"       -> 4 câbles unipolaires de 300 mm² -> section=300
#   "2X3(1x240)"      -> 2 juxtapositions de 3×240 mm²   -> section=240
#   "4X3(1x300)"      -> 4 juxtapositions de 3×300 mm²   -> section=300
#   "3X(1x150)+T70"   -> 3 uni. 150 mm² + terre 70 mm²   -> section=150
# ---------------------------------------------------------------------------

# nG pattern  ex. "5G6", "4G2.5"
_CANECO_G = re.compile(r"^(\d+)\s*[Gg]\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)

# nX+T pattern  ex. "3x95+T50"
_CANECO_X_T = re.compile(
    r"^(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\+\s*[Tt]\s*(\d+(?:[.,]\d+)?)"
)

# Multi-câble unipolaire  ex. "3X(1x35)", "2X3(1x240)", "4X3(1x300)+T..."
# Formats :
#   nX(1xS)    -> 3X(1x35)
#   nXm(1xS)   -> 2X3(1x240)  (m cables par phase, pas de X entre m et la parenthese)
_CANECO_MULTI = re.compile(
    r"(\d+)\s*[xX]\s*\d*\s*\(\s*\d+\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\)",
    re.IGNORECASE,
)

# Simple nX pattern  ex. "1x240", "3x95"
_CANECO_X = re.compile(r"^(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)")


def parse_caneco_cable(cable_str: str | None) -> float | None:
    """Extrait la section en mm² de la designation CANECO (champ 'cable').

    Supporte les formats simples (nGx, nX) et les formats multi-câbles
    unipolaires (nX(1xS), nXm(1xS)) utilisés pour les grandes sections.
    Retourne None si le format n'est pas reconnu.
    """
    if not cable_str:
        return None
    s = cable_str.strip()

    # nG (avec PE)
    m = _CANECO_G.match(s)
    if m:
        return float(m.group(2).replace(",", "."))

    # nX+T (unipolaire + terre)
    m = _CANECO_X_T.match(s)
    if m:
        return float(m.group(2).replace(",", "."))

    # Multi-câble unipolaire  ex. "3X(1x35)", "4X3(1x300)"
    m = _CANECO_MULTI.search(s)
    if m:
        return float(m.group(2).replace(",", "."))

    # Simple nX
    m = _CANECO_X.match(s)
    if m:
        return float(m.group(2).replace(",", "."))

    # Fallback : valeur numérique brute  ex. "6", "2.5"
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_caneco_conductors(cable_str: str | None) -> int | None:
    """Extrait le nombre de conducteurs de la designation CANECO."""
    if not cable_str:
        return None
    s = cable_str.strip()

    m = _CANECO_G.match(s) or _CANECO_X_T.match(s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None

    # Multi-câble : retourne nb_circuits × conducteurs_par_phase
    m = _CANECO_MULTI.search(s)
    if m:
        return None  # nombre total de conducteurs non directement utile ici

    m = _CANECO_X.match(s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def parse_caneco_pe_section(cable_str: str | None, phase_section: float | None) -> float | None:
    """Extrait la section du PE depuis la designation.

    Pour les cables nG (ex. 5G6) le PE est egal a la phase.
    Pour les cables nX+Ty (ex. 3x95+T50) le PE est T.
    """
    if not cable_str:
        return None
    s = cable_str.strip()

    m = _CANECO_G.match(s)
    if m:
        return phase_section  # PE = section de phase

    m = _CANECO_X_T.match(s)
    if m:
        return float(m.group(3).replace(",", "."))

    # Multi-câble avec terre  ex. "3X(1x150)+T70"
    m_t = re.search(r"\+\s*[Tt]\s*(\d+(?:[.,]\d+)?)", s)
    if m_t:
        return float(m_t.group(1).replace(",", "."))

    return None


def is_multi_cable_format(cable_str: str | None) -> bool:
    """Retourne True si la designation est un format multi-câble unipolaire."""
    if not cable_str:
        return False
    return bool(_CANECO_MULTI.search(cable_str.strip()))


# ---------------------------------------------------------------------------
# Parsing section bordereau
# ex. "1X240" -> 240.0
# ex. "4X10" -> 10.0  (section de phase)
# ex. "3X95+T50" -> 95.0
# ex. "240" -> 240.0
# ---------------------------------------------------------------------------

_BDX_X_T = re.compile(r"(\d+)[xX](\d+(?:[.,]\d+)?)\+[Tt](\d+(?:[.,]\d+)?)")
_BDX_MULTI = re.compile(
    r"\d+\s*[xX]\s*\d*\s*\(\s*\d+\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\)",
    re.IGNORECASE,
)
_BDX_X = re.compile(r"(\d+)[xX](\d+(?:[.,]\d+)?)")
_BDX_NUM = re.compile(r"(\d+(?:[.,]\d+)?)")


def parse_bordereau_section(section_str: str | None) -> float | None:
    """Extrait la section de phase en mm² depuis detected_section_mm2 du bordereau."""
    if not section_str:
        return None
    s = section_str.strip().upper()

    m = _BDX_X_T.search(s)
    if m:
        return float(m.group(2).replace(",", "."))

    m = _BDX_MULTI.search(s)
    if m:
        return float(m.group(1).replace(",", "."))

    m = _BDX_X.search(s)
    if m:
        return float(m.group(2).replace(",", "."))

    m = _BDX_NUM.search(s)
    if m:
        return float(m.group(1).replace(",", "."))

    return None


# ---------------------------------------------------------------------------
# Normalisation materiau
# ---------------------------------------------------------------------------

def normalize_material(raw: str | None) -> str | None:
    """Retourne 'Cu', 'Al' ou None."""
    if not raw:
        return None
    u = raw.strip().upper()
    if u in ("CU", "COPPER", "CUIVRE"):
        return "Cu"
    if u in ("AL", "ALU", "ALUMINIUM", "ALUMINUM"):
        return "Al"
    return None


# ---------------------------------------------------------------------------
# Section minimale NF C 15-100 selon la section de phase (PE)
# ---------------------------------------------------------------------------

def min_pe_section(phase_mm2: float) -> float:
    """Retourne la section minimale du PE selon NF C 15-100 art. 543.1."""
    if phase_mm2 <= 16:
        return phase_mm2
    if phase_mm2 <= 35:
        return 16.0
    return phase_mm2 / 2.0


# ---------------------------------------------------------------------------
# Classification courbe disjoncteur depuis IrMg/IN
# ---------------------------------------------------------------------------

_CURVE_RANGES = {"B": (3.0, 5.0), "C": (5.0, 10.0), "D": (10.0, 20.0)}
_IR_MG_MAX_VALID = 20.0  # au-delà : données suspectes, pas de classification


def classify_tripping_curve(ir_mg_in: float | None) -> str | None:
    """Retourne 'B', 'C', 'D' ou None si la valeur est hors plage valide."""
    if ir_mg_in is None or ir_mg_in <= 0 or ir_mg_in > _IR_MG_MAX_VALID:
        return None
    for curve, (lo, hi) in _CURVE_RANGES.items():
        if lo <= ir_mg_in <= hi:
            return curve
    # Hors plage mais dans le domaine valide — on approche la borne la plus proche
    if ir_mg_in < 3.0:
        return "B"
    return "D"  # ir_mg_in > 10 mais <= 20
