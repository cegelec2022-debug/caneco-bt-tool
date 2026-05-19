"""Tests de la derivation des tableaux electriques (detection par style)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models.caneco import CanecoLine
from app.services.tableau.builder import (
    derive_tableaux,
    is_tableau_style,
    normalize_repere,
)

_FIELDS = (
    "designation nb_recepteurs consommation ib longueur type_cable cable "
    "neutre pe calibre bloc_coupure bloc_declencheur bloc_differentiel "
    "ir_th_in ir_mg_in icu ame nb_cables_multi repere_aval"
).split()


def make_line(*, repere, amont, style, **kw) -> CanecoLine:
    cl = MagicMock(spec=CanecoLine)
    for f in _FIELDS:
        setattr(cl, f, kw.get(f))
    cl.repere = repere
    cl.amont = amont
    cl.style = style
    return cl


def test_is_tableau_style():
    assert is_tableau_style("Tableau")
    assert is_tableau_style("  TABLEAU ")
    assert is_tableau_style("Armoire divisionnaire")
    assert is_tableau_style("Coffret")
    assert not is_tableau_style("Eclairage")
    assert not is_tableau_style("GRILLE")
    assert not is_tableau_style("Jeu Barres")
    assert not is_tableau_style(None)


def test_seules_les_lignes_style_tableau_sont_des_tableaux():
    lines = [
        make_line(repere="TGBT", amont="AGBT", style="Tableau",
                  designation="Tableau General"),
        make_line(repere="TES1", amont="TGBT", style="Tableau",
                  designation="Tableau Entrepot 1"),
        make_line(repere="1E/TES1", amont="TES1", style="GRILLE"),
        make_line(repere="TES1-1ECL001", amont="1E/TES1", style="Eclairage"),
    ]
    tableaux = derive_tableaux(lines)
    reperes = sorted(t.repere for t in tableaux)
    assert reperes == ["TES1", "TGBT"]  # ni 1E/TES1 ni TES1-1ECL001


def test_dedoublonnage_des_lignes_en_double():
    # Les exports CANECO doublent chaque ligne : un seul tableau attendu.
    lines = [
        make_line(repere="TES1", amont="TGBT", style="Tableau"),
        make_line(repere="TES1", amont="TGBT", style="Tableau"),
    ]
    tableaux = derive_tableaux(lines)
    assert len(tableaux) == 1
    assert tableaux[0].repere == "TES1"


def test_compte_des_circuits_alimentes():
    lines = [
        make_line(repere="TES1", amont="TGBT", style="Tableau"),
        make_line(repere="C1", amont="TES1", style="Eclairage", longueur=10.0),
        make_line(repere="C2", amont="TES1", style="PC", longueur=5.0),
        make_line(repere="C3", amont="AUTRE", style="PC", longueur=99.0),
    ]
    t = derive_tableaux(lines)[0]
    assert t.repere == "TES1"
    assert t.nb_departs == 2
    assert t.longueur_totale_m == 15.0


def test_sections_fiche_completes():
    line = make_line(
        repere="TGBT", amont="AGBT", style="Tableau",
        designation="Tableau General Basse Tension",
        consommation="800kVA", ib=1154.7, longueur=10.0,
        type_cable="U1000AR2V (90C)", cable="4X3X(1x300)", calibre=1250.0,
        bloc_coupure="NS1250N", icu=50.0,
    )
    t = derive_tableaux([line])[0]
    titres = [s["title"] for s in t.sections]
    assert titres == ["Identification", "Puissance", "Cable d'alimentation",
                      "Protection"]
    # IB formate a la francaise avec unite
    puissance = next(s for s in t.sections if s["title"] == "Puissance")
    ib = next(r for r in puissance["rows"] if r["label"].startswith("Courant"))
    assert ib["value"] == "1154,70 A"


def test_normalize_repere():
    assert normalize_repere("  tes1 ") == "TES1"
    assert normalize_repere(None) == ""
