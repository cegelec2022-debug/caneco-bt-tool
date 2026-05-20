"""Carnet de cables presente PAR TABLEAU (format PDF CANECO BT).

Reproduit fidelement la mise en page du PDF "Carnet de cables" produit par
CANECO BT : une section par tableau electrique, avec la liste des departs qui
en sortent, suivant les colonnes officielles :

    Amont | Repere | Longueur | Type de cable | Ame | Nb cables multi |
    Cable | Neutre | PE ou PEN

Cette vue sera reutilisee a l'identique cote Chef de Chantier (Module B),
augmentee d'une colonne "Longueur reelle" saisie sur le terrain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.models.caneco import CanecoLine
from app.models.field_entry import FieldEntry
from app.services.cable_book.builder import _normalize_ame
from app.services.tableau.builder import is_tableau_style, normalize_repere


@dataclass
class DepartRow:
    """Une ligne de depart dans le carnet d'un tableau (vue PDF CANECO)."""

    caneco_line_id: str
    amont: str
    repere: str
    longueur: float | None
    type_cable: str | None
    ame: str
    nb_cables_multi: int | None
    cable: str | None
    neutre: str | None
    pe_pen: str | None
    excel_row_number: int | None
    # Saisie chantier (Module B) : longueur reellement tiree par le Chef
    longueur_realisee: float | None = None
    commentaire_chantier: str | None = None
    saisi_par: str | None = None


@dataclass
class CarnetTableau:
    """Carnet de cables d'un tableau electrique : ses departs (lignes CANECO)."""

    repere: str
    designation: str | None
    departs: list[DepartRow] = field(default_factory=list)

    @property
    def nb_departs(self) -> int:
        return len(self.departs)

    @property
    def longueur_totale_m(self) -> float:
        """Somme des longueurs brutes des departs (vue tableau, pas conducteurs)."""
        return round(sum((d.longueur or 0.0) for d in self.departs), 2)


@dataclass
class CarnetParTableauReport:
    tableaux: list[CarnetTableau]
    nb_tableaux: int
    nb_departs_total: int
    longueur_totale_m: float


def _row_from_line(
    cl: CanecoLine, entry: FieldEntry | None = None
) -> DepartRow:
    """Convertit une ligne CANECO en ligne de depart pour la vue par tableau."""
    return DepartRow(
        caneco_line_id=cl.id,
        amont=(cl.amont or "").strip(),
        repere=(cl.repere or "").strip(),
        longueur=cl.longueur,
        type_cable=(cl.type_cable or "").strip() or None,
        ame=_normalize_ame(cl.ame),
        nb_cables_multi=cl.nb_cables_multi,
        cable=(cl.cable or "").strip() or None,
        neutre=(cl.neutre or "").strip() or None,
        pe_pen=(cl.pe or "").strip() or None,
        excel_row_number=cl.excel_row_number,
        longueur_realisee=entry.longueur_realisee if entry else None,
        commentaire_chantier=entry.commentaire if entry else None,
        saisi_par=entry.saisi_par if entry else None,
    )


def build_carnet_par_tableau(
    caneco_lines: Iterable[CanecoLine],
    *,
    filter_tableau: str | None = None,
    field_entries: Iterable[FieldEntry] | None = None,
) -> CarnetParTableauReport:
    """Construit le carnet de cables groupe par tableau.

    Args:
        caneco_lines: Lignes CANECO d'un export.
        filter_tableau: Si fourni, ne garde que les tableaux dont le repere
            contient cette chaine (recherche insensible casse).

    Returns:
        CarnetParTableauReport : un CarnetTableau par tableau distinct, trie
        par repere. Pour chaque tableau, ses departs sont dans l'ordre du
        fichier source (excel_row_number).
    """
    lines = list(caneco_lines)
    entries_by_line: dict[str, FieldEntry] = {
        e.caneco_line_id: e for e in (field_entries or [])
    }

    # Identifier les vrais tableaux (ligne CANECO de style "Tableau")
    tableau_info: dict[str, tuple[str, str | None]] = {}
    for cl in lines:
        if is_tableau_style(cl.style):
            cle = normalize_repere(cl.repere)
            if cle and cle not in tableau_info:
                tableau_info[cle] = (
                    (cl.repere or "").strip(),
                    (cl.designation or "").strip() or None,
                )

    # Regrouper les lignes par tableau amont (le tableau qui les alimente)
    departs_par_cle: dict[str, list[CanecoLine]] = {cle: [] for cle in tableau_info}
    for cl in lines:
        cle = normalize_repere(cl.amont)
        if cle in tableau_info:
            departs_par_cle[cle].append(cl)

    carnets: list[CarnetTableau] = []
    needle = (filter_tableau or "").strip().upper()
    for cle, (repere, designation) in tableau_info.items():
        if needle and needle not in cle:
            continue
        rows = sorted(
            (
                _row_from_line(cl, entries_by_line.get(cl.id))
                for cl in departs_par_cle[cle]
            ),
            key=lambda r: (r.excel_row_number or 0, r.repere.upper()),
        )
        carnets.append(
            CarnetTableau(repere=repere, designation=designation, departs=rows)
        )

    carnets.sort(key=lambda c: c.repere.upper())

    nb_departs = sum(c.nb_departs for c in carnets)
    longueur = round(sum(c.longueur_totale_m for c in carnets), 2)

    return CarnetParTableauReport(
        tableaux=carnets,
        nb_tableaux=len(carnets),
        nb_departs_total=nb_departs,
        longueur_totale_m=longueur,
    )
