"""Schemas Pydantic pour le moteur de verification."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Requetes
# ---------------------------------------------------------------------------


class VerificationRunCreate(BaseModel):
    """Parametres de declenchement d'une verification."""

    model_config = ConfigDict(extra="forbid")

    caneco_export_id: str
    bordereau_import_id: str
    cps_import_id: str | None = None
    icc_presumed_ka: float | None = None


class GapStatusUpdate(BaseModel):
    """Mise a jour du statut d'un ecart."""

    model_config = ConfigDict(extra="forbid")

    status: str  # ouvert | acquitte | justifie | clos
    comment: str | None = None


# ---------------------------------------------------------------------------
# Reponses
# ---------------------------------------------------------------------------


class GapResponse(BaseModel):
    """Representation complete d'un ecart."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    code: str
    title: str
    severity: str
    description: str
    fields_compared: dict[str, Any] | None
    suggested_action: str | None
    norm_rule_code: str | None
    caneco_line_id: str | None
    bordereau_line_id: str | None
    caneco_repere: str | None
    caneco_amont: str | None
    bordereau_num_prix: str | None
    status: str
    comment: str | None
    resolved_by_id: str | None
    resolved_at: datetime | None
    created_at: datetime


class VerificationRunResponse(BaseModel):
    """Resume d'une execution de verification."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    caneco_export_id: str | None
    bordereau_import_id: str | None
    cps_import_id: str | None
    status: str
    triggered_by: str
    config_snapshot: dict[str, Any] | None
    duration_seconds: float | None
    total_gaps: int | None
    critical_count: int | None
    high_count: int | None
    medium_count: int | None
    info_count: int | None
    error_message: str | None
    created_at: datetime
    created_by_id: str | None


class VerificationRunDetail(VerificationRunResponse):
    """Run avec la liste complete des ecarts."""

    gaps: list[GapResponse]
