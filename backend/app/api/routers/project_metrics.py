"""Endpoint metriques projet — source unique pour tous les KPI.

Exporte ``GET /api/projects/{id}/metrics`` utilise par les onglets Tableaux,
Saisie chantier et le dashboard RA : les chiffres sont calcules en un seul
endroit (service ``project_metrics``) et restent strictement coherents.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.access import ensure_project_access_read
from app.api.deps import get_current_user, get_db
from app.models.caneco import CanecoLine
from app.models.field_entry import FieldEntry
from app.models.user import User
from app.repositories import caneco_repository
from app.services.project_metrics import compute_project_metrics

router = APIRouter(prefix="/api/projects", tags=["project-metrics"])


class ProjectMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nb_tableaux: int
    nb_circuits: int
    nb_circuits_saisis: int
    avancement_pct: float
    longueur_prevue_m: float
    longueur_realisee_m: float


@router.get(
    "/{project_id}/metrics",
    response_model=ProjectMetricsResponse,
)
def get_project_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectMetricsResponse:
    """Renvoie les KPI projet (sources unique)."""
    ensure_project_access_read(db, project_id, current_user)

    exports = caneco_repository.list_for_project(db, project_id)
    if not exports:
        return ProjectMetricsResponse(
            nb_tableaux=0,
            nb_circuits=0,
            nb_circuits_saisis=0,
            avancement_pct=0.0,
            longueur_prevue_m=0.0,
            longueur_realisee_m=0.0,
        )

    lines = (
        db.query(CanecoLine)
        .filter(CanecoLine.export_id == exports[0].id)
        .all()
    )
    line_ids = [cl.id for cl in lines]
    entries = (
        db.query(FieldEntry)
        .filter(FieldEntry.caneco_line_id.in_(line_ids))
        .all()
        if line_ids
        else []
    )
    m = compute_project_metrics(lines, entries)
    return ProjectMetricsResponse(
        nb_tableaux=m.nb_tableaux,
        nb_circuits=m.nb_circuits,
        nb_circuits_saisis=m.nb_circuits_saisis,
        avancement_pct=round(m.avancement_pct, 1),
        longueur_prevue_m=m.longueur_prevue_m,
        longueur_realisee_m=m.longueur_realisee_m,
    )
