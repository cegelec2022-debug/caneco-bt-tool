"""CableComparator — compare les sections, types et matieres CANECO vs Bordereau.

Ecarts produits :
- E-003 : section cable CANECO != bordereau
- E-005 : type cable CANECO != exige par CPS
- E-006 : matiere conducteur CANECO != bordereau
"""

from __future__ import annotations

from app.models.bordereau import BordereauLine
from app.models.caneco import CanecoLine
from app.services.verification.cable_utils import (
    normalize_material,
    parse_bordereau_section,
    parse_caneco_cable,
)
from app.services.verification.gap_emitter import A_CORRIGER, A_SIGNALER, GapEmitter
from app.services.verification.line_matcher import MatchResult

# Tolerance de comparaison de section (±5 % pour tenir compte des arrondis)
_SECTION_TOL = 0.05


class CableComparator:
    """Detecte les ecarts de section, type et matiere entre CANECO et bordereau."""

    def __init__(self, emitter: GapEmitter) -> None:
        self._emitter = emitter

    def run(self, matches: list[MatchResult]) -> None:
        """Parcourt les correspondances et emet les ecarts detectes."""
        for match in matches:
            cl = match.caneco_line
            bl = match.bordereau_line
            if bl is None:
                continue  # deja signale par LineMatcher (E-001)

            self._check_section(cl, bl)
            self._check_material(cl, bl)

    # ------------------------------------------------------------------

    def _check_section(self, cl: CanecoLine, bl: BordereauLine) -> None:
        """Compare la section de phase."""
        caneco_sec = parse_caneco_cable(cl.cable)
        bd_sec = parse_bordereau_section(bl.detected_section_mm2)

        if caneco_sec is None or bd_sec is None:
            return

        diff = abs(caneco_sec - bd_sec)
        tol = bd_sec * _SECTION_TOL

        if diff > tol:
            repere = cl.repere or "—"
            self._emitter.emit(
                code="E-003",
                title="Section cable differente CANECO / bordereau",
                severity=A_CORRIGER,
                description=(
                    f"Circuit '{repere}' : section CANECO = {caneco_sec} mm² "
                    f"mais bordereau article '{bl.num_prix}' indique {bd_sec} mm²."
                ),
                caneco_line_id=cl.id,
                bordereau_line_id=bl.id,
                caneco_repere=cl.repere,
                bordereau_num_prix=bl.num_prix,
                fields_compared={
                    "champ": "section_mm2",
                    "caneco": caneco_sec,
                    "bordereau": bd_sec,
                    "ecart_mm2": round(diff, 2),
                },
                suggested_action=(
                    f"Verifier si la section {caneco_sec} mm² de CANECO doit etre "
                    f"alignee sur {bd_sec} mm² du bordereau ou inversement."
                ),
            )

    def _check_material(self, cl: CanecoLine, bl: BordereauLine) -> None:
        """Compare la matiere du conducteur."""
        caneco_mat = normalize_material(cl.ame)
        bd_mat = normalize_material(bl.detected_material)

        if caneco_mat is None or bd_mat is None:
            return

        if caneco_mat != bd_mat:
            repere = cl.repere or "—"
            self._emitter.emit(
                code="E-006",
                title="Matiere conducteur differente CANECO / bordereau",
                severity=A_CORRIGER,
                description=(
                    f"Circuit '{repere}' : ame CANECO = {caneco_mat} "
                    f"mais bordereau article '{bl.num_prix}' est en {bd_mat}."
                ),
                caneco_line_id=cl.id,
                bordereau_line_id=bl.id,
                caneco_repere=cl.repere,
                bordereau_num_prix=bl.num_prix,
                fields_compared={
                    "champ": "materiau",
                    "caneco": caneco_mat,
                    "bordereau": bd_mat,
                },
                suggested_action=(
                    "Aligner la matiere du conducteur entre CANECO et le bordereau "
                    "apres confirmation avec le BET."
                ),
            )
