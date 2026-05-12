"""Utilitaires de parsing des designations de cables CANECO et bordereau."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Parsing designation cable CANECO BT
# ex. "5G6" -> (5, 6.0, True)   conducteurs=5, section=6.0 mm², avec PE
# ex. "4G2.5" -> (4, 2.5, True)
# ex. "3x95+T50" -> (3, 95.0, False, pe=50.0)
# ex. "1x240" -> (1, 240.0, False)
# ex. "2G1.5" -> (2, 1.5, True)
# ---------------------------------------------------------------------------

_CANECO_G = re.compile(
    r"^(\d+)\s*[Gg]\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_CANECO_X_T = re.compile(
    r"^(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\+\s*[Tt]\s*(\d+(?:[.,]\d+)?)"
)
_CANECO_X = re.compile(
    r"^(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)"
)


def parse_caneco_cable(cable_str: str | None) -> float | None:
    """Extrait la section en mm² de la designation CANECO (champ 'cable').

    Retourne None si le format n'est pas reconnu.
    """
    if not cable_str:
        return None
    s = cable_str.strip()

    m = _CANECO_G.match(s)
    if m:
        return float(m.group(2).replace(",", "."))

    m = _CANECO_X_T.match(s)
    if m:
        return float(m.group(2).replace(",", "."))

    m = _CANECO_X.match(s)
    if m:
        return float(m.group(2).replace(",", "."))

    # Fallback : juste un nombre (ex. "6")
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_caneco_conductors(cable_str: str | None) -> int | None:
    """Extrait le nombre de conducteurs de la designation CANECO."""
    if not cable_str:
        return None
    s = cable_str.strip()
    m = _CANECO_G.match(s) or _CANECO_X_T.match(s) or _CANECO_X.match(s)
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
        # PE = section de phase
        return phase_section

    m = _CANECO_X_T.match(s)
    if m:
        return float(m.group(3).replace(",", "."))

    return None


# ---------------------------------------------------------------------------
# Parsing section bordereau
# ex. "1X240" -> 240.0
# ex. "4X10" -> 10.0  (section de phase)
# ex. "3X95+T50" -> 95.0
# ex. "240" -> 240.0
# ---------------------------------------------------------------------------

_BDX_X_T = re.compile(r"(\d+)[xX](\d+(?:[.,]\d+)?)\+[Tt](\d+(?:[.,]\d+)?)")
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
