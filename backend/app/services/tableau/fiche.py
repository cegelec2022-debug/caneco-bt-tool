"""Construction des donnees de la fiche tableau (vue client, verticale).

La fiche reflete l'export CANECO le plus recent du projet : les sections sont
derivees en direct de la ligne CANECO du tableau (source de verite).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.tableau import Tableau
from app.repositories import caneco_repository
from app.services.tableau.builder import derive_tableaux, normalize_repere


@dataclass
class FicheData:
    """Donnees pretes a l'affichage / au PDF d'une fiche tableau."""

    repere: str
    designation: str | None
    indice: str
    sections: list[dict]

    @property
    def nb_departs(self) -> int:
        return self._nb_departs

    def _set_nb(self, n: int) -> None:
        self._nb_departs = n


def build_fiche_data(db: Session, tableau: Tableau) -> FicheData:
    """Derive la fiche d'un tableau depuis le dernier export CANECO du projet.

    Args:
        db: Session SQLAlchemy.
        tableau: Le tableau cible (lookup par id ou par token).

    Returns:
        FicheData : repere, designation, indice source et sections (themes).
        Si aucun export ne correspond, sections vide (fiche valide mais sans
        donnees plutot qu'une erreur).
    """
    cle = normalize_repere(tableau.repere)
    exports = caneco_repository.list_for_project(db, tableau.project_id)

    for export in exports:  # du plus recent au plus ancien
        lines = caneco_repository.get_all_lines(db, export.id)
        for derived in derive_tableaux(lines):
            if derived.cle == cle:
                fd = FicheData(
                    repere=tableau.repere,
                    designation=derived.designation or tableau.designation,
                    indice=export.indice or "—",
                    sections=derived.sections,
                )
                fd._set_nb(derived.nb_departs)
                return fd

    fd = FicheData(
        repere=tableau.repere,
        designation=tableau.designation,
        indice=exports[0].indice if exports else "—",
        sections=[],
    )
    fd._set_nb(0)
    return fd
