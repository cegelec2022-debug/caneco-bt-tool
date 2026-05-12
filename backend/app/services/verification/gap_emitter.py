"""GapEmitter — formate et accumule les ecarts avant persistance en base."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GapDTO:
    """Objet de transfert representant un ecart avant insertion en base."""

    code: str
    title: str
    severity: str
    description: str
    norm_rule_code: str | None = None
    caneco_line_id: str | None = None
    bordereau_line_id: str | None = None
    caneco_repere: str | None = None
    bordereau_num_prix: str | None = None
    fields_compared: dict[str, Any] | None = None
    suggested_action: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Severites canoniques
# ---------------------------------------------------------------------------

BLOQUANT = "BLOQUANT"
A_CORRIGER = "A_CORRIGER"
A_SIGNALER = "A_SIGNALER"
INFO = "INFO"


class GapEmitter:
    """Collecteur de gaps produits par les differents checkers."""

    def __init__(self) -> None:
        self._gaps: list[GapDTO] = []

    # ------------------------------------------------------------------

    def emit(
        self,
        *,
        code: str,
        title: str,
        severity: str,
        description: str,
        norm_rule_code: str | None = None,
        caneco_line_id: str | None = None,
        bordereau_line_id: str | None = None,
        caneco_repere: str | None = None,
        bordereau_num_prix: str | None = None,
        fields_compared: dict[str, Any] | None = None,
        suggested_action: str | None = None,
    ) -> None:
        """Enregistre un ecart."""
        self._gaps.append(
            GapDTO(
                code=code,
                title=title,
                severity=severity,
                description=description,
                norm_rule_code=norm_rule_code,
                caneco_line_id=caneco_line_id,
                bordereau_line_id=bordereau_line_id,
                caneco_repere=caneco_repere,
                bordereau_num_prix=bordereau_num_prix,
                fields_compared=fields_compared,
                suggested_action=suggested_action,
            )
        )

    @property
    def gaps(self) -> list[GapDTO]:
        return list(self._gaps)

    def count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {BLOQUANT: 0, A_CORRIGER: 0, A_SIGNALER: 0, INFO: 0}
        for g in self._gaps:
            counts[g.severity] = counts.get(g.severity, 0) + 1
        return counts
