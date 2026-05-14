"""Tests du carnet de cables — extraction de parametres et agregation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.caneco import CanecoLine
from app.services.cable_book.builder import (
    build_cable_book,
    extract_cable_parameters,
    normalize_section_display,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def make_line(
    *,
    repere: str = "1E/TGBT",
    repere_aval: str | None = None,
    amont: str | None = "TGBT",
    type_cable: str = "U1000R2V",
    cable: str = "5G6",
    neutre: str | None = None,
    pe: str | None = None,
    longueur: float = 10.0,
    nb_cables_multi: int = 1,
    style: str = "Eclairage",
) -> CanecoLine:
    cl = MagicMock(spec=CanecoLine)
    cl.id = f"cl-{repere}"
    cl.repere = repere
    cl.repere_aval = repere_aval
    cl.amont = amont
    cl.type_cable = type_cable
    cl.cable = cable
    cl.neutre = neutre
    cl.pe = pe
    cl.longueur = longueur
    cl.nb_cables_multi = nb_cables_multi
    cl.style = style
    return cl


# ---------------------------------------------------------------------------
# extract_cable_parameters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cable,expected_conducteurs,expected_paralleles,expected_section",
    [
        ("5G6", 5, 1, 6.0),
        ("4G2.5", 4, 1, 2.5),
        ("3G2,5", 3, 1, 2.5),
        ("3x95+T50", 4, 1, 95.0),
        ("1x240", 1, 1, 240.0),
        ("4x70", 4, 1, 70.0),
        ("3X(1x150)", 1, 3, 150.0),
        ("4X(1x300)", 1, 4, 300.0),
        ("2X3(1x240)", 1, 6, 240.0),
        ("4X3(1x300)", 1, 12, 300.0),
        ("3X(1x150)+T70", 1, 3, 150.0),
        (None, 0, 1, None),
        ("inconnu", 0, 1, None),
    ],
)
def test_extract_cable_parameters(
    cable: str | None,
    expected_conducteurs: int,
    expected_paralleles: int,
    expected_section: float | None,
) -> None:
    p = extract_cable_parameters(cable)
    assert p.nb_conducteurs == expected_conducteurs
    assert p.nb_circuits_paralleles == expected_paralleles
    assert p.section_mm2 == expected_section


def test_normalize_section_display_keeps_format() -> None:
    """La forme CANECO d'origine doit etre preservee, juste trimmee."""
    assert normalize_section_display("5G6") == "5G6"
    assert normalize_section_display("  3X(1x240)  ") == "3X(1x240)"
    assert normalize_section_display("4x70") == "4x70"
    assert normalize_section_display(None) == "—"


# ---------------------------------------------------------------------------
# build_cable_book — agregation
# ---------------------------------------------------------------------------


def test_build_cable_book_aggregates_by_type_and_cable() -> None:
    """Lignes avec meme (type_cable, cable_brut) doivent etre fusionnees."""
    lines = [
        make_line(type_cable="U1000R2V", cable="5G6", longueur=10.0),
        make_line(type_cable="U1000R2V", cable="5G6", longueur=20.0),
        make_line(type_cable="U1000R2V", cable="3G2.5", longueur=5.0),
    ]
    report = build_cable_book(lines)
    assert len(report.entries) == 2
    # Tri par longueur decroissante → 5G6 (30m) avant 3G2.5 (5m)
    assert report.entries[0].cable_caneco == "5G6"
    assert report.entries[0].longueur_totale_m == 30.0
    assert report.entries[0].nb_occurrences == 2
    assert report.entries[1].cable_caneco == "3G2.5"
    assert report.entries[1].longueur_totale_m == 5.0


def test_build_cable_book_multi_cable_paralleles_multiplies_length() -> None:
    """Pour 3X(1x150), la longueur totale = longueur × 3 (3 cables unipolaires)."""
    lines = [
        make_line(type_cable="U1000R2V", cable="3X(1x150)", longueur=100.0),
    ]
    report = build_cable_book(lines)
    assert len(report.entries) == 1
    # 100m × 3 cables unipolaires en parallele = 300m
    assert report.entries[0].longueur_totale_m == 300.0
    assert report.entries[0].nb_circuits_paralleles == 3


def test_build_cable_book_nb_cables_multi_multiplies() -> None:
    """nb_cables_multi de CANECO est aussi pris en compte."""
    lines = [
        make_line(type_cable="U1000R2V", cable="5G6", longueur=10.0, nb_cables_multi=2),
    ]
    report = build_cable_book(lines)
    assert report.entries[0].longueur_totale_m == 20.0  # 10m × 2 cables


def test_build_cable_book_percentage_sums_to_100() -> None:
    lines = [
        make_line(type_cable="U1000R2V", cable="5G6", longueur=70.0),
        make_line(type_cable="U1000R2V", cable="3G2.5", longueur=30.0),
    ]
    report = build_cable_book(lines)
    total_pct = sum(e.pourcentage_du_total for e in report.entries)
    assert round(total_pct, 1) == 100.0


def test_build_cable_book_skips_lines_without_cable() -> None:
    """Tableaux / reserves sans cable ne sont pas comptabilises."""
    lines = [
        make_line(type_cable="—", cable=None, style="Tableau"),
        make_line(type_cable="U1000R2V", cable="5G6", longueur=10.0),
    ]
    report = build_cable_book(lines)
    assert report.nb_lignes_caneco_traitees == 1
    assert len(report.entries) == 1


def test_build_cable_book_filter_repere_aval() -> None:
    """Filtre par tableau aval restreint l'aggregation."""
    lines = [
        make_line(repere="1E/TGBT", repere_aval="TGBT", cable="5G6", longueur=10.0),
        make_line(repere="2E/TES1", repere_aval="TES1", cable="5G6", longueur=20.0),
    ]
    report = build_cable_book(lines, filter_repere_aval="TES1")
    assert len(report.entries) == 1
    assert report.entries[0].longueur_totale_m == 20.0


def test_build_cable_book_top5_and_per_type_stats() -> None:
    lines = [
        make_line(type_cable="U1000R2V", cable="5G6", longueur=50.0),
        make_line(type_cable="U1000R2V", cable="3G2.5", longueur=30.0),
        make_line(type_cable="U1000R2V", cable="3X(1x150)", longueur=10.0),
        make_line(type_cable="CR1-C1", cable="5G16", longueur=20.0),
    ]
    report = build_cable_book(lines)
    assert report.nb_types_cables_distincts == 2
    assert report.longueur_par_type_cable["U1000R2V"] == 50.0 + 30.0 + 10.0 * 3
    assert report.longueur_par_type_cable["CR1-C1"] == 20.0
    assert len(report.top5) == 4
    # Le premier doit etre 5G6 (50m) ou 3X(1x150) (30m) — verifions le tri
    assert report.top5[0].longueur_totale_m >= report.top5[-1].longueur_totale_m


def test_build_cable_book_aval_subtotals() -> None:
    """longueurs_par_aval permet de sortir les sous-totaux par zone/lot."""
    lines = [
        make_line(repere_aval="ZONE_A", type_cable="U1000R2V", cable="5G6", longueur=10.0),
        make_line(repere_aval="ZONE_A", type_cable="U1000R2V", cable="5G6", longueur=15.0),
        make_line(repere_aval="ZONE_B", type_cable="U1000R2V", cable="5G6", longueur=5.0),
    ]
    report = build_cable_book(lines)
    entry = report.entries[0]
    assert entry.longueurs_par_aval == {"ZONE_A": 25.0, "ZONE_B": 5.0}
    assert report.longueur_par_aval["ZONE_A"] == 25.0
    assert report.longueur_par_aval["ZONE_B"] == 5.0
