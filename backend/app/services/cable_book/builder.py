"""Carnet de cables — aggregation des lignes CANECO pour le BE.

Strategie :
- Parse les designations cable CANECO (5G6, 3x95+T50, 4X(1x300), 2X3(1x240))
  pour extraire (nb_circuits_unitaire, nb_conducteurs, section_mm2).
- Conserve la designation CANECO BRUTE pour l'affichage (jamais reformatee).
- Agrege par cle (type_cable, cable_brut) en additionnant les longueurs.
- Calcule la longueur totale = somme(longueur * nb_cables_multi) sur les lignes.
- Produit aussi un report avec top 5, sous-totaux par tableau aval, % du total.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from app.models.caneco import CanecoLine
from app.services.tableau.builder import is_tableau_style, normalize_repere
from app.services.verification.cable_utils import (
    normalize_material,
    parse_caneco_cable,
    parse_caneco_conductors,
)


# ---------------------------------------------------------------------------
# Extraction des parametres cable
# ---------------------------------------------------------------------------

# Patterns reconnaissables pour le carnet (similaires a cable_utils mais retournent
# aussi le nb de conducteurs et le nb de cables paralleles)

_RE_G = re.compile(r"^\s*(\d+)\s*[Gg]\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_RE_X_PE = re.compile(
    r"^\s*(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\+\s*[Tt]\s*(\d+(?:[.,]\d+)?)"
)
# nXm(1xS) ou nX(1xS) — multi-cable unipolaire
_RE_MULTI = re.compile(
    r"^\s*(\d+)\s*[xX]\s*(\d*)\s*\(\s*\d+\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\)",
    re.IGNORECASE,
)
_RE_X = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)")


@dataclass
class CableParameters:
    """Parametres extraits d'une designation cable CANECO."""

    nb_circuits_paralleles: int  # nb de cables en parallele (1 generalement, 3 pour 3X(1x150))
    nb_conducteurs: int           # nb total de conducteurs par circuit (phases + neutre + PE selon format)
    section_mm2: float | None     # section de phase en mm²
    raw: str | None               # designation brute originale


def extract_cable_parameters(cable_str: str | None) -> CableParameters:
    """Extrait les parametres metier d'une designation cable CANECO.

    Args:
        cable_str: Designation brute (ex. "5G6", "3x95+T50", "4X(1x300)", "2X3(1x240)").

    Returns:
        CableParameters avec nb_circuits_paralleles, nb_conducteurs, section_mm2.
        Si non reconnaissable, retourne des valeurs par defaut (1, 0, None).
    """
    if not cable_str:
        return CableParameters(1, 0, None, cable_str)

    s = cable_str.strip()

    # nG : "5G6" -> 5 conducteurs (avec PE), 1 cable parallele, section 6
    m = _RE_G.match(s)
    if m:
        try:
            return CableParameters(
                nb_circuits_paralleles=1,
                nb_conducteurs=int(m.group(1)),
                section_mm2=float(m.group(2).replace(",", ".")),
                raw=s,
            )
        except ValueError:
            pass

    # nX+T : "3x95+T50" -> 3 conducteurs phase + 1 PE = 4, 1 cable, section 95
    m = _RE_X_PE.match(s)
    if m:
        try:
            return CableParameters(
                nb_circuits_paralleles=1,
                nb_conducteurs=int(m.group(1)) + 1,
                section_mm2=float(m.group(2).replace(",", ".")),
                raw=s,
            )
        except ValueError:
            pass

    # Multi-cable unipolaire : "3X(1x150)" = 3 cables, 1 conducteur chacun
    #                         "2X3(1x240)" = 2x3 = 6 cables unipolaires en parallele
    m = _RE_MULTI.match(s)
    if m:
        try:
            n_outer = int(m.group(1))
            n_inner = int(m.group(2)) if m.group(2) else 1
            return CableParameters(
                nb_circuits_paralleles=n_outer * n_inner,
                nb_conducteurs=1,
                section_mm2=float(m.group(3).replace(",", ".")),
                raw=s,
            )
        except ValueError:
            pass

    # nX simple : "3x95", "1x240"
    m = _RE_X.match(s)
    if m:
        try:
            return CableParameters(
                nb_circuits_paralleles=1,
                nb_conducteurs=int(m.group(1)),
                section_mm2=float(m.group(2).replace(",", ".")),
                raw=s,
            )
        except ValueError:
            pass

    # Fallback : juste un nombre brut
    try:
        return CableParameters(1, 0, float(s.replace(",", ".")), s)
    except ValueError:
        return CableParameters(1, 0, None, s)


def normalize_section_display(cable_str: str | None) -> str:
    """Retourne la designation cable nettoyee pour affichage (espaces, casse).

    Garde le format CANECO d'origine (5G6, 3X(1x240)) sans le reformater.
    Remplace seulement les virgules decimales par des points dans les nombres.
    """
    if not cable_str:
        return "—"
    s = cable_str.strip()
    # Pas de transformation : on garde le format CANECO brut
    return s


# ---------------------------------------------------------------------------
# Agregation : entree du carnet et report
# ---------------------------------------------------------------------------


@dataclass
class CableBookEntry:
    """Une ligne du sommaire du carnet de cables — un (type_cable, cable_brut) unique."""

    type_cable: str               # ex. "U1000R2V"
    cable_caneco: str             # designation brute CANECO ex. "5G6" ou "4X(1x300)"
    section_mm2: float | None     # section de phase
    nb_conducteurs: int           # nb conducteurs par circuit (info)
    nb_circuits_paralleles: int   # nb cables unipolaires en parallele par circuit
    longueur_totale_m: float      # somme des longueurs (longueur * nb_cables_multi)
    nb_occurrences: int           # nb de lignes CANECO sources qui ont contribue
    reperes_aval: set[str] = field(default_factory=set)  # ensemble des tableaux aval traverses

    # Repartition par tableau aval (pour les sous-totaux par zone/lot)
    longueurs_par_aval: dict[str, float] = field(default_factory=dict)

    @property
    def pourcentage_du_total(self) -> float:
        """Calcule a posteriori via build_cable_book (necessite le total)."""
        return getattr(self, "_pct", 0.0)


@dataclass
class CableBookReport:
    """Rapport synthetique global du carnet de cables."""

    entries: list[CableBookEntry]
    longueur_totale_projet_m: float
    nb_lignes_caneco_traitees: int
    nb_types_cables_distincts: int
    longueur_par_type_cable: dict[str, float]    # {type_cable: longueur_totale}
    longueur_par_aval: dict[str, float]          # {repere_aval: longueur_totale}
    top5: list[CableBookEntry]                    # top 5 par longueur totale


def build_cable_book(
    caneco_lines: Iterable[CanecoLine],
    *,
    filter_repere_aval: str | None = None,
) -> CableBookReport:
    """Aggrege les lignes CANECO en un carnet de cables complet.

    Args:
        caneco_lines: Lignes CANECO d'un export (issues de la base).
        filter_repere_aval: Si fourni, ne garde que les lignes dont le tableau aval
            (ou le repere) contient cette chaine. Utile pour cibler une zone/lot.

    Returns:
        CableBookReport avec entries triees par longueur totale decroissante et stats.
    """
    lines = list(caneco_lines)

    # Ensemble des reperes de vrais tableaux (style = Tableau/Armoire/Coffret).
    # Le sommaire "par tableau aval" ne doit regrouper que des tableaux, jamais
    # des circuits (1E/TES1, TES1-1ECL001...).
    tableau_keys = {
        normalize_repere(cl.repere) for cl in lines if is_tableau_style(cl.style)
    }

    def _tableau_parent(cl: CanecoLine) -> str | None:
        """Tableau de rattachement d'une ligne (amont si c'est un tableau)."""
        for candidate in (cl.amont, cl.repere_aval, cl.repere):
            cand = (candidate or "").strip()
            if cand and normalize_repere(cand) in tableau_keys:
                return cand
        return None

    # Agregation par cle (type_cable, cable_brut_normalise)
    buckets: dict[tuple[str, str], CableBookEntry] = {}

    nb_lignes_traitees = 0

    for cl in lines:
        # Filtre par tableau aval si demande
        if filter_repere_aval:
            haystack = " ".join(
                filter(None, [cl.repere_aval, cl.repere, cl.amont])
            ).upper()
            if filter_repere_aval.upper() not in haystack:
                continue

        # Skip lignes sans cable (tableaux, reserves)
        if not cl.cable:
            continue

        type_cable = (cl.type_cable or "—").strip() or "—"
        cable_brut = normalize_section_display(cl.cable)
        params = extract_cable_parameters(cl.cable)

        # Longueur unitaire et nb cables paralleles
        longueur_unit = cl.longueur or 0.0
        nb_cables_multi = cl.nb_cables_multi or 1
        if nb_cables_multi <= 0:
            nb_cables_multi = 1

        # Longueur totale apportee par cette ligne
        # = longueur unitaire × nb_cables_multi × nb_circuits_paralleles_format
        # nb_circuits_paralleles_format vient de 3X(1x150) = 3, etc.
        longueur_apport = (
            longueur_unit * nb_cables_multi * params.nb_circuits_paralleles
        )

        key = (type_cable, cable_brut)
        entry = buckets.get(key)
        if entry is None:
            entry = CableBookEntry(
                type_cable=type_cable,
                cable_caneco=cable_brut,
                section_mm2=params.section_mm2,
                nb_conducteurs=params.nb_conducteurs,
                nb_circuits_paralleles=params.nb_circuits_paralleles,
                longueur_totale_m=0.0,
                nb_occurrences=0,
            )
            buckets[key] = entry

        entry.longueur_totale_m += longueur_apport
        entry.nb_occurrences += 1

        # Rattachement au tableau parent (jamais a un circuit)
        aval = _tableau_parent(cl)
        if aval:
            entry.reperes_aval.add(aval)
            entry.longueurs_par_aval[aval] = (
                entry.longueurs_par_aval.get(aval, 0.0) + longueur_apport
            )

        nb_lignes_traitees += 1

    entries = sorted(
        buckets.values(),
        key=lambda e: e.longueur_totale_m,
        reverse=True,
    )

    # Calcul du total et des pourcentages
    total = sum(e.longueur_totale_m for e in entries)
    for e in entries:
        e._pct = (e.longueur_totale_m / total * 100.0) if total > 0 else 0.0

    # Stats globales
    longueur_par_type: dict[str, float] = defaultdict(float)
    longueur_par_aval: dict[str, float] = defaultdict(float)
    for e in entries:
        longueur_par_type[e.type_cable] += e.longueur_totale_m
        for aval, lg in e.longueurs_par_aval.items():
            longueur_par_aval[aval] += lg

    top5 = entries[:5]

    return CableBookReport(
        entries=entries,
        longueur_totale_projet_m=total,
        nb_lignes_caneco_traitees=nb_lignes_traitees,
        nb_types_cables_distincts=len({e.type_cable for e in entries}),
        longueur_par_type_cable=dict(longueur_par_type),
        longueur_par_aval=dict(longueur_par_aval),
        top5=top5,
    )
