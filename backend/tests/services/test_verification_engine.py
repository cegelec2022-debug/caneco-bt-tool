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
    min_pe_section,
    normalize_material,
    parse_bordereau_section,
    parse_caneco_cable,
    parse_caneco_conductors,
)
from app.services.verification.gap_emitter import BLOQUANT, A_CORRIGER, GapEmitter
from app.services.verification.line_matcher import LineMatcher
from app.services.verification.norm_checker import NormChecker
from app.services.verification.protection_checker import ProtectionChecker, _next_standard_calibre
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


def test_protection_icu_insufficient() -> None:
    emitter = GapEmitter()
    cl = make_caneco(ib=8.0, calibre=10.0, icu=3.0)
    checker = ProtectionChecker(emitter, icc_presumed_ka=6.0)
    checker.run([cl])
    codes = [g.code for g in emitter.gaps]
    assert "E-011" in codes


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
