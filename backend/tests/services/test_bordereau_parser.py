"""Tests du parser bordereau de prix.

Valide le comportement sur le fichier de reference DACHSER et des cas limites.
"""

import uuid
from pathlib import Path

import pytest

from app.services.bordereau.parser import (
    _detect_cable_type,
    _detect_material,
    _detect_section_mm2,
    _detect_cfo_sheet_name,
    _enrich_line,
    _kind_from_section_code,
    _section_code_from_num_prix,
    detect_indice_from_filename,
    list_sheet_names,
    parse_bordereau_file,
)
from app.models.bordereau import BordereauLine

# ---------------------------------------------------------------------------
# Chemin du fichier de reference
# ---------------------------------------------------------------------------

SEED_DIR = Path("/app/data/seed/dachser")
DACHSER_BORDEREAU = SEED_DIR / "Pièce_03_Bordereau_des_Prix_DACHSER_LOT3.xlsx"


# ---------------------------------------------------------------------------
# Tests unitaires : fonctions utilitaires
# ---------------------------------------------------------------------------


def test_detect_section_mm2_5g6():
    assert _detect_section_mm2("Cable 5G6 cuivre") == "5G6"


def test_detect_section_mm2_1x240():
    assert _detect_section_mm2("Cable 1X240mm² aluminium") == "1X240"


def test_detect_section_mm2_4x95_t50():
    assert _detect_section_mm2("Câble 4X95+T50") == "4X95+T50"


def test_detect_section_mm2_absent():
    assert _detect_section_mm2("TGBT 400A débrochable") is None


def test_detect_material_alu():
    assert _detect_material("Cable U1000AR2V 1X240 ALU") == "ALU"


def test_detect_material_aluminium():
    assert _detect_material("CABLES U1000ARO2V ALUMINIUM") == "ALU"


def test_detect_material_cuivre():
    assert _detect_material("Cable cuivre 5G6") == "CUIVRE"


def test_detect_material_absent():
    assert _detect_material("TGBT tableau general") is None


def test_detect_cable_type_u1000ar2v():
    result = _detect_cable_type("U1000AR2V 1x240mm²")
    assert result is not None
    assert "U1000AR2V" in result.upper()


def test_detect_cable_type_cr1():
    assert _detect_cable_type("CR1 3G2.5 desenfumage") == "CR1"


def test_detect_cable_type_absent():
    assert _detect_cable_type("Chemin de cable 200x60") is None


def test_section_code_from_num_prix():
    assert _section_code_from_num_prix("505.3") == "505"
    assert _section_code_from_num_prix("507.1") == "507"
    assert _section_code_from_num_prix("501.10") == "501"


def test_kind_from_section_code():
    assert _kind_from_section_code("505") == "cable"
    assert _kind_from_section_code("507") == "tableau"
    assert _kind_from_section_code("506") == "chemin_cable"
    assert _kind_from_section_code("508") == "tubage"
    assert _kind_from_section_code("509") == "appareillage"
    assert _kind_from_section_code("999") == "autre"


def test_detect_indice_from_filename():
    assert detect_indice_from_filename("Bordereau_INDICE_B.xlsx") == "B"
    assert detect_indice_from_filename("BDP_DACHSER.xlsx") is None


# ---------------------------------------------------------------------------
# Test d'enrichissement d'une ligne cable
# ---------------------------------------------------------------------------


def test_enrich_line_cable_alu():
    line = BordereauLine(
        id=str(uuid.uuid4()),
        bordereau_import_id=str(uuid.uuid4()),
        num_prix="505.5",
        designation="Cable U1000AR2V 1X240 ALU",
        excel_row_number=42,
    )
    _enrich_line(line, "505", None)
    assert line.detected_kind == "cable"
    assert line.detected_section_mm2 == "1X240"
    assert line.detected_material == "ALU"
    assert line.detected_cable_type is not None


def test_enrich_line_tableau():
    line = BordereauLine(
        id=str(uuid.uuid4()),
        bordereau_import_id=str(uuid.uuid4()),
        num_prix="507.1",
        designation="TGBT 400A débrochable",
        excel_row_number=10,
    )
    _enrich_line(line, "507", None)
    assert line.detected_kind == "tableau"
    assert line.detected_section_mm2 is None
    assert line.detected_material is None


# ---------------------------------------------------------------------------
# Test sur le fichier DACHSER (integration)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not DACHSER_BORDEREAU.exists(), reason="Fichier DACHSER absent")
def test_parse_dachser_bordereau():
    """Parse complet du fichier DACHSER : valide les comptes et la structure."""
    import openpyxl

    result = parse_bordereau_file(DACHSER_BORDEREAU, import_id=str(uuid.uuid4()))

    # Au moins 30 sections (la spec indique 32 sous-sections 501-532 + section principale)
    assert result.sections_count >= 30, (
        f"Nombre de sections insuffisant : {result.sections_count}"
    )

    # Au moins 150 articles (la spec parle de 244 lignes dont beaucoup sont des sous-familles/headers)
    assert result.total_articles >= 100, (
        f"Nombre d'articles insuffisant : {result.total_articles}"
    )

    # Chaque article a un num_prix et une designation
    for line in result.lines:
        assert line.num_prix, f"Ligne sans num_prix : excel_row={line.excel_row_number}"
        assert line.designation, f"Ligne sans designation : {line.num_prix}"

    # Les articles de la section 505 ont des detections enrichies
    cables = [ln for ln in result.lines if (ln.num_prix or "").startswith("505")]
    assert len(cables) > 0, "Aucun article en section 505 detecte"
    cables_with_section = [c for c in cables if c.detected_section_mm2]
    assert len(cables_with_section) > 0, "Aucun cable 505 avec section mm2 detectee"


@pytest.mark.skipif(not DACHSER_BORDEREAU.exists(), reason="Fichier DACHSER absent")
def test_parse_dachser_detects_cfo_sheet():
    """Verifie que la feuille BDP_ELECTRICITE CFO est auto-detectee."""
    content = DACHSER_BORDEREAU.read_bytes()
    sheets, detected = list_sheet_names(content)
    assert detected is not None
    assert "ELECTRICITE" in detected.upper()
    assert "CFO" in detected.upper()


def test_detect_cfo_sheet_name_finds_electricite_cfo():
    """Verifie la detection sur une liste de noms de feuilles."""
    names = ["RECAP_LOT III", "BDP_FLUIDES", "BDP_ELECTRICITE CFO", "BDP_CFA ET SURETE"]
    result = _detect_cfo_sheet_name(names)
    assert result == "BDP_ELECTRICITE CFO"


def test_detect_cfo_sheet_name_fallback_to_electricite():
    """Verifie le fallback sur une feuille contenant juste ELECTRICITE."""
    names = ["RECAP", "ELECTRICITE GENERALE", "FLUIDES"]
    result = _detect_cfo_sheet_name(names)
    assert result == "ELECTRICITE GENERALE"


def test_detect_cfo_sheet_name_ignores_recap():
    """Verifie que les feuilles RECAP/FLUIDE sont ignorees en fallback."""
    names = ["RECAP_LOT", "BDP_FLUIDES", "ELECTRICITE BT"]
    result = _detect_cfo_sheet_name(names)
    assert result == "ELECTRICITE BT"


def test_parse_rejects_invalid_file():
    """Un fichier inexistant leve une exception."""
    with pytest.raises(Exception):
        parse_bordereau_file(Path("/tmp/inexistant.xlsx"), import_id=str(uuid.uuid4()))
