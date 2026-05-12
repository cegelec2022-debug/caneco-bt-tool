"""LineMatcher — rapprochement CANECO <-> Bordereau.

Strategie :
- Tableaux CANECO (style contient 'tableau' ou designation entre parentheses dans bordereau)
  -> match par repere extrait de la designation bordereau ex. "(TES1)" -> "TES1"
- Circuits CANECO -> match bordereau cable par section + materiau
- Signale les circuits CANECO sans equivalent bordereau (E-001)
- Signale les articles bordereau cable/tableau sans equivalent CANECO (E-002, E-013)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.bordereau import BordereauLine
from app.models.caneco import CanecoLine
from app.services.verification.cable_utils import (
    normalize_material,
    parse_bordereau_section,
    parse_caneco_cable,
)
from app.services.verification.gap_emitter import A_CORRIGER, A_SIGNALER, INFO, GapEmitter

# Regex extrayant un repere entre parentheses depuis la designation bordereau
_RE_REPERE = re.compile(r"\(([A-Z0-9_\-]{2,30})\)", re.IGNORECASE)

# Styles CANECO qui correspondent a un tableau ou a une ligne hors-circuit
_TABLEAU_STYLES = {
    "tableau", "td", "tgbt", "tgt", "tds", "armoire", "coffret",
    "distribution", "bus", "jeu de barres", "jdb",
    "reserve", "réserve", "parafoudre", "paraf",
}


def _is_tableau_style(style: str | None) -> bool:
    if not style:
        return False
    sl = style.strip().lower()
    return any(k in sl for k in _TABLEAU_STYLES)


@dataclass
class MatchResult:
    caneco_line: CanecoLine
    bordereau_line: BordereauLine | None


@dataclass
class MatchReport:
    matched: list[MatchResult] = field(default_factory=list)
    unmatched_caneco: list[CanecoLine] = field(default_factory=list)
    unmatched_bordereau: list[BordereauLine] = field(default_factory=list)


class LineMatcher:
    """Rapproche les lignes CANECO aux lignes bordereau."""

    def __init__(
        self,
        caneco_lines: list[CanecoLine],
        bordereau_lines: list[BordereauLine],
        emitter: GapEmitter,
    ) -> None:
        self._caneco = caneco_lines
        self._bordereau = bordereau_lines
        self._emitter = emitter

    # ------------------------------------------------------------------

    def run(self) -> MatchReport:
        report = MatchReport()

        # Separe tableaux et circuits CANECO
        tableau_caneco = [l for l in self._caneco if _is_tableau_style(l.style)]
        circuit_caneco = [l for l in self._caneco if not _is_tableau_style(l.style)]

        # Separe tableaux et cables bordereau
        bd_tableaux = [
            l for l in self._bordereau if (l.detected_kind or "") in ("tableau",)
        ]
        bd_cables = [
            l for l in self._bordereau if (l.detected_kind or "") in ("cable",)
        ]

        matched_bd_ids: set[str] = set()

        # --- Rapprochement tableaux ---
        for cl in tableau_caneco:
            repere = (cl.repere or "").strip().upper()
            bd_match = self._find_tableau_in_bordereau(repere, bd_tableaux, matched_bd_ids)
            if bd_match:
                matched_bd_ids.add(bd_match.id)
                report.matched.append(MatchResult(cl, bd_match))
            else:
                report.unmatched_caneco.append(cl)
                self._emitter.emit(
                    code="E-013",
                    title="Tableau CANECO absent du bordereau",
                    severity=A_CORRIGER,
                    description=(
                        f"Le tableau '{repere}' est present dans l'export CANECO "
                        f"mais aucun article 'tableau' correspondant n'a ete trouve dans le bordereau."
                    ),
                    caneco_line_id=cl.id,
                    caneco_repere=cl.repere,
                    suggested_action=(
                        "Verifier que le tableau est bien prevu au bordereau "
                        "ou qu'il ne s'agit pas d'un tableau de renvoi."
                    ),
                )

        # --- Rapprochement circuits par section + materiau ---
        # Construit un index bordereau : (section_mm2, materiau) -> list[BordereauLine]
        bd_index: dict[tuple[float, str], list[BordereauLine]] = {}
        for bl in bd_cables:
            sec = parse_bordereau_section(bl.detected_section_mm2)
            mat = normalize_material(bl.detected_material) or "Cu"
            if sec is not None:
                key = (sec, mat)
                bd_index.setdefault(key, []).append(bl)

        for cl in circuit_caneco:
            sec = parse_caneco_cable(cl.cable)
            mat = normalize_material(cl.ame) or "Cu"
            bd_match = None
            if sec is not None:
                key = (sec, mat)
                candidates = [b for b in bd_index.get(key, []) if b.id not in matched_bd_ids]
                if candidates:
                    bd_match = candidates[0]
                    matched_bd_ids.add(bd_match.id)

            report.matched.append(MatchResult(cl, bd_match))
            if bd_match is None:
                report.unmatched_caneco.append(cl)
                repere = cl.repere or "—"
                if sec is None:
                    # Section non parsable : signaler sans bloquer (format inconnu ou ligne vide)
                    self._emitter.emit(
                        code="E-001",
                        title="Circuit CANECO absent du bordereau (section non identifiee)",
                        severity=INFO,
                        description=(
                            f"Le circuit '{repere}' (designation cable : '{cl.cable or '—'}') "
                            f"n'a pas pu etre rapproche du bordereau car la section n'a pas ete "
                            f"reconnue dans la designation."
                        ),
                        caneco_line_id=cl.id,
                        caneco_repere=cl.repere,
                        fields_compared={"cable_brut": cl.cable, "materiau": mat},
                        suggested_action=(
                            "Verifier manuellement si un article bordereau correspond "
                            f"a ce circuit (designation cable : '{cl.cable or '—'}')."
                        ),
                    )
                else:
                    self._emitter.emit(
                        code="E-001",
                        title="Circuit CANECO absent du bordereau",
                        severity=A_SIGNALER,
                        description=(
                            f"Le circuit '{repere}' (section {sec} mm², {mat}) est dans CANECO "
                            f"mais n'a pas d'article cable correspondant dans le bordereau."
                        ),
                        caneco_line_id=cl.id,
                        caneco_repere=cl.repere,
                        fields_compared={"section_mm2": sec, "materiau": mat},
                        suggested_action=(
                            "Verifier si un article de section equivalente existe "
                            "sous une autre designation dans le bordereau."
                        ),
                    )

        # --- Articles bordereau sans equivalent CANECO ---
        for bl in bd_cables + bd_tableaux:
            if bl.id not in matched_bd_ids:
                report.unmatched_bordereau.append(bl)
                code = "E-013" if bl.detected_kind == "tableau" else "E-002"
                title = (
                    "Tableau bordereau absent de CANECO"
                    if bl.detected_kind == "tableau"
                    else "Cable bordereau sans circuit CANECO associe"
                )
                self._emitter.emit(
                    code=code,
                    title=title,
                    severity=A_SIGNALER,
                    description=(
                        f"L'article bordereau '{bl.num_prix}' ({bl.designation or ''}) "
                        f"n'a pas de correspondant dans l'export CANECO."
                    ),
                    bordereau_line_id=bl.id,
                    bordereau_num_prix=bl.num_prix,
                    suggested_action=(
                        "Verifier si la ligne bordereau correspond a un circuit non exporte "
                        "ou a un article commun (fourreaux, tiges filetees, etc.)."
                    ),
                )

        return report

    # ------------------------------------------------------------------

    @staticmethod
    def _find_tableau_in_bordereau(
        repere: str,
        bd_tableaux: list[BordereauLine],
        already_matched: set[str],
    ) -> BordereauLine | None:
        """Cherche un article tableau dans le bordereau par repere."""
        for bl in bd_tableaux:
            if bl.id in already_matched:
                continue
            designation = (bl.designation or "").upper()
            # Cherche "(TES1)" ou "TES1" dans la designation
            m = _RE_REPERE.search(designation)
            if m and m.group(1).upper() == repere:
                return bl
            if repere and repere in designation:
                return bl
        return None
