"""Source UNIQUE des chiffres de chantier d'un projet.

Garanti la coherence entre tous les ecrans qui affichent des indicateurs :
- Onglet Tableaux (KPI tableaux / circuits / longueur cumulee)
- Onglet Saisie chantier (KPI circuits saisis / total / avancement)
- Onglet Stock cables (utilisation auto-calculee)
- Tableau de bord RA (resume par projet)

Conventions metier (uniformes) :

- *Tableau* : ligne CANECO dont ``style`` est un type de jeu de barres
  (Tableau, Armoire, Coffret), dedoublonne par repere normalise.
- *Circuit* : ligne CANECO dont ``style`` n'est pas un tableau ET dont
  ``amont`` correspond a un repere de tableau reel du projet. Les
  sous-tableaux (style=Tableau, amont=autre tableau) sont comptes parmi les
  tableaux, JAMAIS comme circuits.
- *Longueur prevue* (CANECO) : somme methode CANECO BT (decomposition
  unipolaire + neutre + PE + multiplicateurs paralleles) sur tous les
  circuits du projet. C'est la veritable longueur de cable du projet,
  comparable au PDF CANECO officiel et coherente avec le carnet de cables.
- *Longueur realisee* (CANECO) : meme decomposition appliquee a la longueur
  reellement saisie sur chaque circuit (proportionnellement a sa longueur
  prevue brute).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models.caneco import CanecoLine
from app.models.field_entry import FieldEntry
from app.services.cable_book.builder import _contributions_for_line, build_cable_book
from app.services.tableau.builder import _dedupe, is_tableau_style, normalize_repere


def caneco_length_prevue(all_lines: list[CanecoLine]) -> float:
    """Longueur totale projet = methode CANECO sur toutes les lignes (= carnet).

    Inclut les cables d'alimentation entre tableaux, les jeux de barres, etc.
    Coherent avec le carnet de cables et le PDF officiel CANECO BT.
    """
    return round(build_cable_book(all_lines).longueur_totale_projet_m, 2)


def caneco_length_realisee(
    circuits: list[CanecoLine],
    entries_by_line: dict[str, FieldEntry],
) -> float:
    """Longueur reellement tiree (methode CANECO) sur les circuits saisis.

    Pour chaque circuit saisi, on applique le meme ratio de longueur reelle /
    longueur prevue brute a CHAQUE contribution unipolaire / Neutre / PE de la
    ligne — exactement comme dans le suivi du stock cable.
    """
    total = 0.0
    for cl in circuits:
        e = entries_by_line.get(cl.id)
        if e is None:
            continue
        prevue = float(cl.longueur or 0.0)
        contribs = _contributions_for_line(cl)
        if not contribs:
            continue
        if prevue <= 0:
            total += float(e.longueur_realisee)
            continue
        ratio = float(e.longueur_realisee) / prevue
        for c in contribs:
            total += c.longueur * ratio
    return round(total, 2)


@dataclass
class ProjectMetrics:
    """Indicateurs de chantier d'un projet, source unique pour toute l'app."""

    nb_tableaux: int
    nb_circuits: int
    nb_circuits_saisis: int
    longueur_prevue_m: float
    longueur_realisee_m: float

    @property
    def avancement_pct(self) -> float:
        return (
            (self.nb_circuits_saisis / self.nb_circuits * 100.0)
            if self.nb_circuits > 0
            else 0.0
        )


def collect_circuits(
    caneco_lines: Iterable[CanecoLine],
) -> tuple[set[str], list[CanecoLine]]:
    """Renvoie (reperes de tableaux, lignes circuits) selon la convention metier.

    Args:
        caneco_lines: Lignes CANECO d'un export (brutes, non dedoublonnees).

    Returns:
        - ``tableau_keys`` : ensemble des reperes (normalises) des tableaux du
          projet (style = Tableau / Armoire / Coffret).
        - ``circuits`` : lignes non-tableau dont l'amont correspond a un
          tableau du projet, sur l'export dedoublonne.
    """
    lines = _dedupe(caneco_lines)
    tableau_keys = {
        normalize_repere(cl.repere) for cl in lines if is_tableau_style(cl.style)
    }
    circuits = [
        cl
        for cl in lines
        if not is_tableau_style(cl.style)
        and normalize_repere(cl.amont) in tableau_keys
    ]
    return tableau_keys, circuits


def compute_project_metrics(
    caneco_lines: Iterable[CanecoLine],
    field_entries: Iterable[FieldEntry],
) -> ProjectMetrics:
    """Calcule les indicateurs cles d'un projet a partir des donnees brutes."""
    tableau_keys, circuits = collect_circuits(caneco_lines)
    entries_by_line = {e.caneco_line_id: e for e in field_entries}

    nb_circuits_saisis = sum(1 for cl in circuits if cl.id in entries_by_line)
    # Pour la longueur prevue : on utilise TOUTES les lignes (= total carnet)
    # afin de coller au PDF CANECO. Pour la longueur realisee : on n'a de
    # saisies que sur les circuits, on ventile selon la decomposition CANECO.
    all_lines = _dedupe(caneco_lines)
    return ProjectMetrics(
        nb_tableaux=len(tableau_keys),
        nb_circuits=len(circuits),
        nb_circuits_saisis=nb_circuits_saisis,
        longueur_prevue_m=caneco_length_prevue(all_lines),
        longueur_realisee_m=caneco_length_realisee(circuits, entries_by_line),
    )
