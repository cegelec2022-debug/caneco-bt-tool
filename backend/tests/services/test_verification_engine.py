"""Tests du moteur de verification croisee.

Couvre :
- cable_utils : parsing designations cables CANECO et bordereau
- GapEmitter : collecte et comptage
- CableComparator : detection ecarts section et matiere
- ProtectionChecker : IB > In, Icu < Icc, IrTh
- NormChecker : section minimale, PE, courbe
- SuggestionEngine : surdimensionnement, longueur
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.bordereau import BordereauLine
from app.models.caneco import CanecoLine
from app.services.verification.cable_comparator import CableComparator
from app.services.verification.cable_utils import (
    classify_tripping_curve,
    min_pe_section,
    normalize_material,
    parse_bordereau_section,
    parse_caneco_cable,
    parse_caneco_conductors,
)
from app.services.verification.gap_emitter import BLOQUANT, A_CORRIGER, GapEmitter
from app.services.verification.line_matcher import (
    LineMatcher,
    _extract_parent_tableau,
    _parse_simple_section,
)
from app.services.verification.norm_checker import NormChecker
from app.services.verification.protection_checker import (
    ProtectionChecker,
    _next_standard_calibre,
    compute_depth_map,
)
from app.services.verification.suggestion_engine import SuggestionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_caneco(
    *,
    repere: str = "TES1-D1",
    style: str = "Eclairage",
    cable: str = "2G1.5",
    ame: str = "Cu",
    ib: float = 8.0,
    calibre: float = 10.0,
    icu: float = 10.0,
    ir_mg_in: float = 5.0,
    ir_th_in: float = 0.9,
    longueur: float = 20.0,
    amont: str | None = None,
    bloc_differentiel: str | None = None,
    neutre: str | None = None,
    pe: str | None = None,
    type_cable: str | None = "U1000R2V",
    designation: str | None = None,
) -> CanecoLine:
    cl = MagicMock(spec=CanecoLine)
    cl.id = f"cl-{repere}"
    cl.repere = repere
    cl.style = style
    cl.cable = cable
    cl.ame = ame
    cl.ib = ib
    cl.calibre = calibre
    cl.icu = icu
    cl.ir_mg_in = ir_mg_in
    cl.ir_th_in = ir_th_in
    cl.longueur = longueur
    cl.amont = amont
    cl.bloc_differentiel = bloc_differentiel
    cl.neutre = neutre
    cl.pe = pe
    cl.type_cable = type_cable
    cl.designation = designation
    cl.excel_row_number = None
    return cl


def make_bordereau(
    *,
    num_prix: str = "505.1",
    designation: str = "Cable U1000R2V 3G2.5 Cu",
    detected_section_mm2: str = "3X2.5",
    detected_material: str = "CU",
    detected_kind: str = "cable",
) -> BordereauLine:
    bl = MagicMock(spec=BordereauLine)
    bl.id = f"bl-{num_prix}"
    bl.num_prix = num_prix
    bl.designation = designation
    bl.detected_section_mm2 = detected_section_mm2
    bl.detected_material = detected_material
    bl.detected_kind = detected_kind
    return bl


# ---------------------------------------------------------------------------
# cable_utils
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cable,expected",
    [
        ("5G6", 6.0),
        ("4G2.5", 2.5),
        ("3x95+T50", 95.0),
        ("1x240", 240.0),
        ("2G1.5", 1.5),
        ("6", 6.0),
        (None, None),
        ("inconnu", None),
        # Multi-cable unipolaire (grandes sections DACHSER)
        ("3X(1x35)", 35.0),
        ("4X(1x300)", 300.0),
        ("2X3(1x240)", 240.0),
        ("4X3(1x300)", 300.0),
        ("3X(1x150)+T70", 150.0),
    ],
)
def test_parse_caneco_cable(cable: str | None, expected: float | None) -> None:
    assert parse_caneco_cable(cable) == expected


@pytest.mark.parametrize(
    "section_str,expected",
    [
        ("3X2.5", 2.5),
        ("1X240", 240.0),
        ("4X10", 10.0),
        ("3X95+T50", 95.0),
        ("240", 240.0),
        (None, None),
    ],
)
def test_parse_bordereau_section(section_str: str | None, expected: float | None) -> None:
    assert parse_bordereau_section(section_str) == expected


def test_parse_caneco_conductors() -> None:
    assert parse_caneco_conductors("5G6") == 5
    assert parse_caneco_conductors("4G2.5") == 4
    assert parse_caneco_conductors("3x95+T50") == 3
    assert parse_caneco_conductors(None) is None


@pytest.mark.parametrize(
    "material,expected",
    [
        ("Cu", "Cu"),
        ("CU", "Cu"),
        ("cuivre", "Cu"),
        ("Al", "Al"),
        ("ALU", "Al"),
        ("aluminium", "Al"),
        (None, None),
        ("acier", None),
    ],
)
def test_normalize_material(material: str | None, expected: str | None) -> None:
    assert normalize_material(material) == expected


@pytest.mark.parametrize(
    "phase,expected_pe",
    [
        (1.5, 1.5),
        (6.0, 6.0),
        (16.0, 16.0),
        (25.0, 16.0),
        (35.0, 16.0),
        (50.0, 25.0),
        (95.0, 47.5),
        (240.0, 120.0),
    ],
)
def test_min_pe_section(phase: float, expected_pe: float) -> None:
    assert min_pe_section(phase) == pytest.approx(expected_pe)


# ---------------------------------------------------------------------------
# GapEmitter
# ---------------------------------------------------------------------------


def test_gap_emitter_collect() -> None:
    emitter = GapEmitter()
    emitter.emit(code="E-001", title="Test", severity=BLOQUANT, description="desc")
    emitter.emit(code="E-004", title="Test2", severity=A_CORRIGER, description="desc2")
    assert len(emitter.gaps) == 2
    assert emitter.gaps[0].code == "E-001"


def test_gap_emitter_count_by_severity() -> None:
    emitter = GapEmitter()
    emitter.emit(code="E-001", title="T", severity="BLOQUANT", description="d")
    emitter.emit(code="E-001", title="T", severity="BLOQUANT", description="d")
    emitter.emit(code="E-004", title="T", severity="A_CORRIGER", description="d")
    counts = emitter.count_by_severity()
    assert counts["BLOQUANT"] == 2
    assert counts["A_CORRIGER"] == 1


# ---------------------------------------------------------------------------
# CableComparator
# ---------------------------------------------------------------------------


def test_cable_comparator_section_mismatch() -> None:
    emitter = GapEmitter()
    cl = make_caneco(cable="3x6", ame="Cu")
    bl = make_bordereau(detected_section_mm2="3X10", detected_material="CU")
    from app.services.verification.line_matcher import MatchResult
    comp = CableComparator(emitter)
    comp.run([MatchResult(cl, bl)])
    codes = [g.code for g in emitter.gaps]
    assert "E-003" in codes


def test_cable_comparator_material_mismatch() -> None:
    emitter = GapEmitter()
    cl = make_caneco(cable="3x95", ame="Al")
    bl = make_bordereau(detected_section_mm2="3X95", detected_material="CU")
    from app.services.verification.line_matcher import MatchResult
    comp = CableComparator(emitter)
    comp.run([MatchResult(cl, bl)])
    codes = [g.code for g in emitter.gaps]
    assert "E-006" in codes


def test_cable_comparator_no_gap_same_section() -> None:
    emitter = GapEmitter()
    cl = make_caneco(cable="4G2.5", ame="Cu")
    bl = make_bordereau(detected_section_mm2="4X2.5", detected_material="CU")
    from app.services.verification.line_matcher import MatchResult
    comp = CableComparator(emitter)
    comp.run([MatchResult(cl, bl)])
    assert len(emitter.gaps) == 0


# ---------------------------------------------------------------------------
# ProtectionChecker
# ---------------------------------------------------------------------------


def test_protection_ib_gt_calibre() -> None:
    emitter = GapEmitter()
    cl = make_caneco(ib=20.0, calibre=16.0, icu=10.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    codes = [g.code for g in emitter.gaps]
    assert "E-004" in codes


def test_protection_icu_null_emits_e019() -> None:
    """v1.3 : Icu=0 ou None emet E-019 (donnee manquante CANECO), plus de E-011."""
    emitter = GapEmitter()
    cl = make_caneco(ib=8.0, calibre=10.0, icu=0.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    codes = [g.code for g in emitter.gaps]
    assert "E-019" in codes
    # E-011 supprime : on ne compare plus Icc et Icu
    assert "E-011" not in codes


def test_protection_icu_valid_no_gap() -> None:
    """Icu correctement renseigne (meme faible) ne genere pas E-019."""
    emitter = GapEmitter()
    cl = make_caneco(ib=8.0, calibre=10.0, icu=4.5)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    icu_gaps = [g for g in emitter.gaps if g.code in ("E-011", "E-019") and "Icu" in g.title]
    assert icu_gaps == []


def test_protection_ok_no_gaps() -> None:
    emitter = GapEmitter()
    cl = make_caneco(ib=8.0, calibre=10.0, icu=10.0, ir_th_in=0.9)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    assert len(emitter.gaps) == 0


def test_next_standard_calibre() -> None:
    assert _next_standard_calibre(8.5) == 10.0
    assert _next_standard_calibre(16.0) == 16.0
    assert _next_standard_calibre(33.0) == 40.0


# ---------------------------------------------------------------------------
# NormChecker — section minimale
# ---------------------------------------------------------------------------


def test_norm_checker_min_section_eclairage() -> None:
    emitter = GapEmitter()
    cl = make_caneco(repere="ECL-1", style="Eclairage", cable="2G1", ame="Cu")
    checker = NormChecker(emitter)
    checker.run([cl])
    codes = [g.code for g in emitter.gaps]
    assert "E-008" in codes


def test_norm_checker_ok_section() -> None:
    emitter = GapEmitter()
    cl = make_caneco(repere="ECL-1", style="Eclairage", cable="2G1.5", ame="Cu")
    checker = NormChecker(emitter)
    checker.run([cl])
    # Pas de E-008 pour section minimale (1.5 mm² = OK pour eclairage)
    section_gaps = [g for g in emitter.gaps if g.code == "E-008" and "Section" in g.title]
    assert len(section_gaps) == 0


# ---------------------------------------------------------------------------
# SuggestionEngine
# ---------------------------------------------------------------------------


def test_suggestion_oversized_section() -> None:
    emitter = GapEmitter()
    # Calibre 10 A -> section minimale normative ~1.5 mm², section 16 mm² = surdim
    cl = make_caneco(cable="2G16", calibre=10.0, ib=8.0, longueur=5.0)
    engine = SuggestionEngine(emitter)
    engine.run([cl])
    codes = [g.code for g in emitter.gaps]
    assert "E-010" in codes


def test_suggestion_long_cable() -> None:
    emitter = GapEmitter()
    cl = make_caneco(longueur=60.0, calibre=16.0, ib=12.0)
    engine = SuggestionEngine(emitter)
    engine.run([cl])
    titles = [g.title for g in emitter.gaps]
    assert any("longueur" in t.lower() for t in titles)


# ---------------------------------------------------------------------------
# classify_tripping_curve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ir_mg_in,expected_curve",
    [
        (4.0, "B"),    # milieu plage B
        (5.0, "B"),    # borne basse C = borne haute B → attribuee a B
        (7.5, "C"),    # milieu plage C
        (10.0, "C"),   # borne haute C
        (15.0, "D"),   # milieu plage D
        (2.0, "B"),    # sous la plage B → approche borne la plus proche
        (None, None),  # valeur absente
        (0.0, None),   # zero invalide
        (96.0, None),  # DACHSER : valeur anormalement haute → pas de courbe
        (25.0, None),  # au-dela de la plage valide
    ],
)
def test_classify_tripping_curve(ir_mg_in: float | None, expected_curve: str | None) -> None:
    assert classify_tripping_curve(ir_mg_in) == expected_curve


# ---------------------------------------------------------------------------
# ProtectionChecker — cas limites
# ---------------------------------------------------------------------------


def test_protection_ib_zero_emits_e019() -> None:
    """v1.3 : IB=0 sur un circuit hors-tableau emet E-019 (oubli de calcul CANECO)."""
    emitter = GapEmitter()
    cl = make_caneco(ib=0.0, calibre=10.0, icu=10.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    codes = [g.code for g in emitter.gaps]
    assert "E-019" in codes
    # Pas de E-004 IB>In (ib=0 ne depasse pas calibre)
    e004 = [g for g in emitter.gaps if g.code == "E-004"]
    assert e004 == []


def test_protection_skips_tableau_style() -> None:
    """Les lignes de style 'Tableau' ne doivent pas etre verifiees."""
    emitter = GapEmitter()
    # IB > calibre, mais style Tableau → pas d'ecart
    cl = make_caneco(style="TGBT", ib=500.0, calibre=10.0, icu=10.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    assert len(emitter.gaps) == 0


def test_protection_skips_reserve_style() -> None:
    """Les lignes de style 'Reserve' ne doivent pas etre verifiees."""
    emitter = GapEmitter()
    cl = make_caneco(style="Reserve", ib=0.0, calibre=10.0, icu=10.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    assert len(emitter.gaps) == 0


# ---------------------------------------------------------------------------
# A — _extract_parent_tableau (matching hierarchique)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "repere,expected_parent",
    [
        ("TGBTDIV005", "TGBT"),
        ("TES1DIV009", "TES1"),
        ("TGBTSJB008", "TGBT"),
        ("TADMRDIV011", "TADMR"),
        ("TADMRRG02", "TADMR"),
        ("THVACDIV001", "THVAC"),
        ("TFRIGODIV001", "TFRIGO"),
        ("TGBT", None),
        ("TES1", None),
        ("TE-AUX-PT", None),
        ("TE-CLIM-ADM", None),
        ("", None),
    ],
)
def test_extract_parent_tableau(repere: str, expected_parent: str | None) -> None:
    assert _extract_parent_tableau(repere) == expected_parent


# ---------------------------------------------------------------------------
# D — compute_depth_map (Icc degressif)
# ---------------------------------------------------------------------------


def test_compute_depth_map_simple_arborescence() -> None:
    """TGBT (0) -> TES1 (1) -> 1E/TES1 (2)."""
    tgbt = make_caneco(repere="TGBT", style="Tableau", amont=None)
    tes1 = make_caneco(repere="TES1", style="Tableau", amont="TGBT")
    ces1 = make_caneco(repere="1E/TES1", style="Eclairage", amont="TES1")
    depth = compute_depth_map([tgbt, tes1, ces1])
    assert depth[tgbt.id] == 0
    assert depth[tes1.id] == 1
    assert depth[ces1.id] == 2


def test_compute_depth_map_orphan_returns_zero() -> None:
    """Une ligne sans amont reconnu a une profondeur de 0."""
    cl = make_caneco(repere="ORPHAN", amont="UNKNOWN_PARENT")
    depth = compute_depth_map([cl])
    assert depth[cl.id] == 0


def test_protection_no_more_e011_with_valid_icu() -> None:
    """v1.3 : Icu valide ne genere plus E-011, peu importe la profondeur (Icc non compare)."""
    emitter = GapEmitter()
    cl = make_caneco(repere="DEEP", style="Eclairage", ib=8.0, calibre=10.0, icu=4.5)
    checker = ProtectionChecker(emitter, icc_presumed_ka=25.0, depth_map={cl.id: 0})
    checker.run([cl])
    e011 = [g for g in emitter.gaps if g.code == "E-011"]
    assert e011 == []


# ---------------------------------------------------------------------------
# C — NormChecker filtre par domaine d'installation
# ---------------------------------------------------------------------------


def test_norm_checker_nfc012_skipped_in_tertiaire() -> None:
    """NFC-012 (DDR prises 30 mA habitation) n'est pas appliquee en tertiaire."""
    emitter = GapEmitter()
    # Style 'prise' + calibre 16 A + pas de DDR : NFC-012 declencherait en habitation
    cl = make_caneco(repere="P1", style="prise", calibre=16.0, bloc_differentiel=None)
    checker = NormChecker(emitter, domaine_installation="tertiaire")
    checker.run([cl])
    e007 = [g for g in emitter.gaps if g.code == "E-007" and g.norm_rule_code == "NFC-012"]
    assert e007 == []


def test_norm_checker_nfc012_applied_in_habitation() -> None:
    """NFC-012 est appliquee en habitation (severite A_SIGNALER avec note context)."""
    emitter = GapEmitter()
    cl = make_caneco(repere="P1", style="prise", calibre=16.0, bloc_differentiel=None)
    checker = NormChecker(emitter, domaine_installation="habitation")
    checker.run([cl])
    e007 = [g for g in emitter.gaps if g.code == "E-007" and g.norm_rule_code == "NFC-012"]
    assert len(e007) >= 1


# ---------------------------------------------------------------------------
# B — NFC-013 mots-cles stricts (locaux humides)
# ---------------------------------------------------------------------------


def test_norm_checker_nfc013_does_not_match_sm() -> None:
    """'SM' (ex. Service Maintenance) ne doit pas declencher NFC-013 locaux humides."""
    emitter = GapEmitter()
    cl = make_caneco(repere="2SM/TADMR", style="prise", designation="Prise SM Service",
                     bloc_differentiel=None)
    checker = NormChecker(emitter, domaine_installation="tertiaire")
    checker.run([cl])
    nfc013 = [g for g in emitter.gaps if g.norm_rule_code == "NFC-013"]
    assert nfc013 == []


def test_norm_checker_nfc013_matches_real_douche() -> None:
    """'Douche' dans la designation doit declencher NFC-013."""
    emitter = GapEmitter()
    cl = make_caneco(repere="DCH1", style="Eclairage", designation="Eclairage douche RDC",
                     bloc_differentiel=None)
    checker = NormChecker(emitter, domaine_installation="tertiaire")
    checker.run([cl])
    nfc013 = [g for g in emitter.gaps if g.norm_rule_code == "NFC-013"]
    assert len(nfc013) >= 1


# ---------------------------------------------------------------------------
# I — _parse_simple_section et couverture des sections phase/neutre/PE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1x70", 70.0),
        ("1x150", 150.0),
        ("70", 70.0),
        ("2.5", 2.5),
        ("G16", 16.0),
        ("gG70", 70.0),
        (None, None),
        ("", None),
        ("inconnu", None),
    ],
)
def test_parse_simple_section(raw: str | None, expected: float | None) -> None:
    assert _parse_simple_section(raw) == expected


# ---------------------------------------------------------------------------
# G — caneco_amont propage dans les gaps
# ---------------------------------------------------------------------------


def test_gap_includes_caneco_amont() -> None:
    """Tout gap emis doit porter l'amont (tableau d'origine) pour l'identification."""
    emitter = GapEmitter()
    cl = make_caneco(repere="1E/TGBT", amont="TGBT", ib=20.0, calibre=16.0, icu=10.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    e004 = [g for g in emitter.gaps if g.code == "E-004"]
    assert len(e004) >= 1
    # Tous les gaps doivent porter l'amont
    for g in e004:
        assert g.caneco_amont == "TGBT", f"Gap '{g.title}' missing amont"


def test_e019_missing_icu_includes_amont() -> None:
    """E-019 sur Icu nul propage egalement l'amont."""
    emitter = GapEmitter()
    cl = make_caneco(repere="6E/TGBT", amont="TGBT", ib=5.0, calibre=10.0, icu=0.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    e019 = [g for g in emitter.gaps if g.code == "E-019" and "Icu" in g.title]
    assert len(e019) == 1
    assert e019[0].caneco_amont == "TGBT"


# ---------------------------------------------------------------------------
# L — Numero de ligne Excel CANECO propage dans les gaps
# ---------------------------------------------------------------------------


def test_gap_includes_excel_row() -> None:
    """Le gap porte le numero de ligne Excel CANECO pour l'identification."""
    emitter = GapEmitter()
    cl = make_caneco(repere="1E/TGBT", amont="TGBT", ib=20.0, calibre=16.0, icu=10.0)
    cl.excel_row_number = 42
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    e004 = [g for g in emitter.gaps if g.code == "E-004"]
    assert len(e004) >= 1
    for g in e004:
        assert g.caneco_row == 42, f"Gap '{g.title}' missing caneco_row"
