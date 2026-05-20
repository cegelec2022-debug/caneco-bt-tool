"""Carnet de cables — methode CANECO (decomposition en conducteurs).

Reproduit fidelement la structure du recapitulatif "Carnet de cables" produit
par CANECO BT (cf. PDF officiel) : chaque ligne CANECO est decomposee en
conducteurs unipolaires de section distincte. La somme du carnet est
strictement comparable au PDF CANECO (utile pour chiffrage et commande).

Regles de decomposition (par ligne CANECO) :

- Cable multipolaire ``nG<S>`` (3G2,5, 5G16, 4G6...) :
  -> 1 contribution sous la cle (type, "nG<S>", ame), de longueur
     ``L * nb_cables_multi``.

- Cable multipolaire avec PE separe ``nx<S>+T<P>`` (3x95+T50...) :
  -> 1 contribution multipolaire (type, "nx<S>+T<P>", ame), ``L * NCM``.

- Cable en parallele ``nX(1xS)`` ou ``nXm(1xS)`` (3X(1x150), 2X3X(1x240)...) :
  -> ``n * m`` contributions sous la cle (type, "1*<S> mm²", ame),
     longueur ``L * NCM * n * m``. C'est exactement la decomposition que
     CANECO presente dans son recap (chaque conducteur unipolaire compte).

- Pour CHAQUE ligne, on ajoute aussi les conducteurs Neutre et PE/PEN
  renseignes dans les colonnes 12 et 13 (souvent ``1x240``, ``1x150``...).
  CANECO les compte comme cables unipolaires distincts dans le recap.

Le label de la section affichee :
- "<n>G<S>" pour les multipolaires (5G6, 3G2,5...)
- "1*<S> mm²" pour les unipolaires (style CANECO BT v5.x)
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from app.models.caneco import CanecoLine
from app.services.tableau.builder import is_tableau_style, normalize_repere
from app.services.verification.cable_utils import (  # noqa: F401 (re-export utilises ailleurs)
    normalize_material,
    parse_caneco_cable,
    parse_caneco_conductors,
)


# ---------------------------------------------------------------------------
# Reconnaissance des designations CANECO
# ---------------------------------------------------------------------------

_RE_G = re.compile(r"^\s*(\d+)\s*[Gg]\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_RE_X_PE = re.compile(
    r"^\s*(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\+\s*[Tt]\s*(\d+(?:[.,]\d+)?)"
)
# nX(1xS) ou nXm(1xS) (le m optionnel peut etre separe par 'X' ou non) :
# "3X(1x150)" -> n=3, m=1 ; "2X3X(1x240)" -> n=2, m=3 ; "4X3(1x240)" -> n=4, m=3
_RE_MULTI = re.compile(
    r"^\s*(\d+)\s*[xX]\s*(\d*)\s*[xX]?\s*\(\s*\d+\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*\)",
    re.IGNORECASE,
)
_RE_X = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)")
# Conducteur Neutre ou PE/PEN : "1x240", "240", "1*240 mm²"...
_RE_COND = re.compile(
    r"^\s*(?:(\d+)\s*[xX*])?\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE
)
# Cable deja au format unipolaire CANECO ("1*240 mm²", "1*70mm²", "1*150 mm²")
_RE_UNIPOLAIRE_DIRECT = re.compile(
    r"^\s*1\s*\*\s*(\d+(?:[.,]\d+)?)\s*mm",
    re.IGNORECASE,
)

_AME_LABEL = {
    "1": "Cuivre",
    "2": "Alu",
    "cu": "Cuivre",
    "al": "Alu",
    "cuivre": "Cuivre",
    "alu": "Alu",
}


def _normalize_ame(value: object) -> str:
    """Convertit la valeur Ame brute (code 1/2 ou libelle) en 'Cuivre' / 'Alu'."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    # Le champ peut etre stocke en float ("1.0", "2.0")
    if s.endswith(".0"):
        s = s[:-2]
    return _AME_LABEL.get(s, s.title() if s else "")


def _fmt_section(value: float) -> str:
    """Affiche une section en mm² : '240' ou '2,5' (style CANECO)."""
    if value.is_integer():
        return str(int(value))
    return f"{value:g}".replace(".", ",")


def _label_unipolaire(section: float) -> str:
    """Etiquette CANECO pour un conducteur unipolaire : '1*240 mm²'."""
    return f"1*{_fmt_section(section)} mm²"


@dataclass
class CableParameters:
    """Parametres extraits d'une designation cable CANECO (info technique)."""

    nb_circuits_paralleles: int
    nb_conducteurs: int
    section_mm2: float | None
    raw: str | None


def extract_cable_parameters(cable_str: str | None) -> CableParameters:
    """Extrait les parametres techniques d'une designation cable CANECO.

    Args:
        cable_str: ``5G6``, ``3x95+T50``, ``4X(1x300)``, ``2X3X(1x240)``...

    Returns:
        CableParameters. Si non reconnu, valeurs par defaut (1, 0, None).
    """
    if not cable_str:
        return CableParameters(1, 0, None, cable_str)
    s = cable_str.strip()

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

    try:
        return CableParameters(1, 0, float(s.replace(",", ".")), s)
    except ValueError:
        return CableParameters(1, 0, None, s)


def normalize_section_display(cable_str: str | None) -> str:
    """Designation cable nettoyee pour affichage (espaces, casse preserves)."""
    if not cable_str:
        return "—"
    return cable_str.strip()


# ---------------------------------------------------------------------------
# Decomposition d'une ligne CANECO en contributions au carnet
# ---------------------------------------------------------------------------


@dataclass
class _Contribution:
    """Une contribution unitaire au sommaire du carnet (apres decomposition)."""

    type_cable: str
    section_label: str      # "3G2,5" (multi) ou "1*240 mm²" (unipolaire)
    ame: str                # "Cuivre" / "Alu" / ""
    section_mm2: float | None
    nb_conducteurs: int     # nb conducteurs par cable affiche (1 unipolaire, 3 pour 3G..)
    longueur: float         # longueur deja multipliee par les facteurs


def _decompose_conductor(
    conductor: str | None,
    *,
    type_cable: str,
    ame: str,
    length_unit: float,
    nb_cables_multi: int,
) -> _Contribution | None:
    """Decompose une valeur Neutre ou PE/PEN en une contribution unipolaire.

    Reconnait :
    - ``1x240``, ``240`` : un conducteur de section S
    - ``2X(1x240)`` : n conducteurs unipolaires de section S (cas frequent
      pour le PE des cables parallele)
    - ``2X3(1x240)`` : n*m conducteurs unipolaires de section S

    Args:
        conductor: Valeur brute (peut etre vide).
        type_cable: Type du cable parent (reutilise pour le regroupement).
        ame: Ame du cable parent.
        length_unit: Longueur de la ligne CANECO.
        nb_cables_multi: Nb cables multi de la ligne CANECO (souvent non
            applique au PE — voir contributions_for_line).

    Returns:
        La contribution unipolaire correspondante, ou None si non interpretable.
    """
    if not conductor:
        return None
    s = str(conductor).strip()
    if not s:
        return None

    # Format ``nX(1xS)`` ou ``nXm(1xS)`` (PE des cables paralleles)
    m = _RE_MULTI.match(s)
    if m:
        try:
            n_outer = int(m.group(1))
            n_inner = int(m.group(2)) if m.group(2) else 1
            section = float(m.group(3).replace(",", "."))
        except (ValueError, TypeError):
            return None
        if section <= 0 or n_outer * n_inner <= 0:
            return None
        return _Contribution(
            type_cable=type_cable,
            section_label=_label_unipolaire(section),
            ame=ame,
            section_mm2=section,
            nb_conducteurs=1,
            longueur=length_unit * nb_cables_multi * n_outer * n_inner,
        )

    # Format simple ``1x240``, ``240`` ou ``1*240 mm²``
    m_uni = _RE_UNIPOLAIRE_DIRECT.match(s)
    if m_uni:
        try:
            section = float(m_uni.group(1).replace(",", "."))
        except (ValueError, TypeError):
            return None
        if section <= 0:
            return None
        return _Contribution(
            type_cable=type_cable,
            section_label=_label_unipolaire(section),
            ame=ame,
            section_mm2=section,
            nb_conducteurs=1,
            longueur=length_unit * nb_cables_multi,
        )
    m = _RE_COND.match(s)
    if not m:
        return None
    try:
        n = int(m.group(1)) if m.group(1) else 1
        section = float(m.group(2).replace(",", "."))
    except (ValueError, TypeError):
        return None
    if section <= 0:
        return None
    return _Contribution(
        type_cable=type_cable,
        section_label=_label_unipolaire(section),
        ame=ame,
        section_mm2=section,
        nb_conducteurs=1,
        longueur=length_unit * nb_cables_multi * n,
    )


def _contributions_for_line(cl: CanecoLine) -> list[_Contribution]:
    """Decompose une ligne CANECO en contributions au carnet (cf. methode CANECO)."""
    cable = (cl.cable or "").strip()
    if not cable:
        return []

    type_cable = (cl.type_cable or "—").strip() or "—"
    ame = _normalize_ame(cl.ame)
    longueur_unit = float(cl.longueur or 0.0)
    ncm = int(cl.nb_cables_multi or 1) or 1
    if ncm <= 0:
        ncm = 1

    contributions: list[_Contribution] = []

    # 1) Decomposition du cable principal.
    #
    # Note importante : dans la convention CANECO BT, `nb_cables_multi` est
    # une simple copie du `n` exterieur de la notation parallele
    # ``nXm(1xS)`` (par ex. ``2X3X(1x240)`` -> NCM=2, 2X3X(1xS) lui-meme
    # encode 2*3=6 conducteurs). Le multiplier en plus revient a un double
    # comptage. Pour les multipolaires ``nG<S>`` / ``nx<S>+T<P>`` (NCM=1
    # dans tous les exports observes), on conserve `* NCM` pour gerer
    # theoriquement un cas ou plusieurs cables multipolaires identiques
    # seraient tires en parallele.
    # Cas particulier : cable deja au format unipolaire "1*240 mm²" dans la
    # colonne Cable — 1 conducteur de section S, longueur brute * NCM.
    if (m_uni := _RE_UNIPOLAIRE_DIRECT.match(cable)):
        try:
            section = float(m_uni.group(1).replace(",", "."))
        except ValueError:
            section = 0.0
        if section > 0:
            contributions.append(
                _Contribution(
                    type_cable=type_cable,
                    section_label=_label_unipolaire(section),
                    ame=ame,
                    section_mm2=section,
                    nb_conducteurs=1,
                    longueur=longueur_unit * ncm,
                )
            )
    elif (m := _RE_MULTI.match(cable)):
        # Unipolaires en parallele : n*m conducteurs de section S.
        try:
            n_outer = int(m.group(1))
            n_inner = int(m.group(2)) if m.group(2) else 1
            section = float(m.group(3).replace(",", "."))
        except ValueError:
            n_outer = n_inner = 0
            section = 0
        if n_outer * n_inner > 0 and section > 0:
            contributions.append(
                _Contribution(
                    type_cable=type_cable,
                    section_label=_label_unipolaire(section),
                    ame=ame,
                    section_mm2=section,
                    nb_conducteurs=1,
                    longueur=longueur_unit * n_outer * n_inner,
                )
            )
    else:
        # Multipolaire (nG<S>, nx<S>+T<P>, nx<S>) : 1 ligne brute au recap.
        params = extract_cable_parameters(cable)
        contributions.append(
            _Contribution(
                type_cable=type_cable,
                section_label=cable,
                ame=ame,
                section_mm2=params.section_mm2,
                nb_conducteurs=params.nb_conducteurs,
                longueur=longueur_unit * ncm,
            )
        )

    # 2) Conducteurs Neutre / PE / PEN (separes — comme dans le recap CANECO).
    # Pas de multiplication par NCM : ce sont des sous-conducteurs propres
    # a la ligne (leur propre prefixe ``nX`` porte deja le nb de conducteurs).
    for cond in (cl.neutre, cl.pe):
        c = _decompose_conductor(
            cond,
            type_cable=type_cable,
            ame=ame,
            length_unit=longueur_unit,
            nb_cables_multi=1,
        )
        if c is not None:
            contributions.append(c)

    return contributions


# ---------------------------------------------------------------------------
# Modeles publics : entree du carnet et report
# ---------------------------------------------------------------------------


@dataclass
class CableBookEntry:
    """Une ligne du sommaire du carnet — un (type, section_label, ame) unique."""

    type_cable: str
    cable_caneco: str               # libelle affiche : "3G2,5" ou "1*240 mm²"
    section_mm2: float | None
    nb_conducteurs: int
    nb_circuits_paralleles: int     # toujours 1 dans le format CANECO (decompose)
    longueur_totale_m: float
    nb_occurrences: int
    reperes_aval: set[str] = field(default_factory=set)
    longueurs_par_aval: dict[str, float] = field(default_factory=dict)
    ame: str = ""                   # "Cuivre" / "Alu" / ""

    @property
    def pourcentage_du_total(self) -> float:
        return getattr(self, "_pct", 0.0)


@dataclass
class CableBookReport:
    entries: list[CableBookEntry]
    longueur_totale_projet_m: float
    nb_lignes_caneco_traitees: int
    nb_types_cables_distincts: int
    longueur_par_type_cable: dict[str, float]
    longueur_par_aval: dict[str, float]
    top5: list[CableBookEntry]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_cable_book(
    caneco_lines: Iterable[CanecoLine],
    *,
    filter_repere_aval: str | None = None,
) -> CableBookReport:
    """Aggrege les lignes CANECO en un carnet de cables (methode CANECO).

    Args:
        caneco_lines: Lignes CANECO d'un export.
        filter_repere_aval: Si fourni, ne garde que les lignes dont le tableau
            aval / amont / repere contient la chaine. Utile pour cibler un lot.

    Returns:
        CableBookReport avec entries triees par longueur decroissante et stats.
    """
    lines = list(caneco_lines)

    # Tableaux reels (regroupement aval = uniquement par tableau, jamais circuit)
    tableau_keys = {
        normalize_repere(cl.repere) for cl in lines if is_tableau_style(cl.style)
    }

    def _tableau_parent(cl: CanecoLine) -> str | None:
        for candidate in (cl.amont, cl.repere_aval, cl.repere):
            cand = (candidate or "").strip()
            if cand and normalize_repere(cand) in tableau_keys:
                return cand
        return None

    buckets: dict[tuple[str, str, str], CableBookEntry] = {}
    nb_lignes_traitees = 0

    for cl in lines:
        if filter_repere_aval:
            haystack = " ".join(
                filter(None, [cl.repere_aval, cl.repere, cl.amont])
            ).upper()
            if filter_repere_aval.upper() not in haystack:
                continue

        contribs = _contributions_for_line(cl)
        if not contribs:
            continue

        aval = _tableau_parent(cl)

        for c in contribs:
            key = (c.type_cable, c.section_label, c.ame)
            entry = buckets.get(key)
            if entry is None:
                entry = CableBookEntry(
                    type_cable=c.type_cable,
                    cable_caneco=c.section_label,
                    section_mm2=c.section_mm2,
                    nb_conducteurs=c.nb_conducteurs,
                    nb_circuits_paralleles=1,
                    longueur_totale_m=0.0,
                    nb_occurrences=0,
                    ame=c.ame,
                )
                buckets[key] = entry

            entry.longueur_totale_m += c.longueur
            entry.nb_occurrences += 1

            if aval:
                entry.reperes_aval.add(aval)
                entry.longueurs_par_aval[aval] = (
                    entry.longueurs_par_aval.get(aval, 0.0) + c.longueur
                )

        nb_lignes_traitees += 1

    entries = sorted(
        buckets.values(),
        key=lambda e: e.longueur_totale_m,
        reverse=True,
    )

    total = sum(e.longueur_totale_m for e in entries)
    for e in entries:
        e._pct = (e.longueur_totale_m / total * 100.0) if total > 0 else 0.0

    longueur_par_type: dict[str, float] = defaultdict(float)
    longueur_par_aval: dict[str, float] = defaultdict(float)
    for e in entries:
        longueur_par_type[e.type_cable] += e.longueur_totale_m
        for aval, lg in e.longueurs_par_aval.items():
            longueur_par_aval[aval] += lg

    return CableBookReport(
        entries=entries,
        longueur_totale_projet_m=total,
        nb_lignes_caneco_traitees=nb_lignes_traitees,
        nb_types_cables_distincts=len({e.type_cable for e in entries}),
        longueur_par_type_cable=dict(longueur_par_type),
        longueur_par_aval=dict(longueur_par_aval),
        top5=entries[:5],
    )
