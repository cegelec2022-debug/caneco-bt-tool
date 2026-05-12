"""Endpoints verification — declenchement, consultation et gestion des ecarts."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User, UserRole
from app.models.verification import Gap, VerificationRun
from app.repositories import (
    caneco_repository,
    project_repository,
    verification_repository,
)
from app.repositories.verification_repository import (
    get_gap_by_id,
    get_gaps_for_run,
    get_run_by_id,
    get_runs_for_project,
    update_gap_status,
)
from app.schemas.verification import (
    GapResponse,
    GapStatusUpdate,
    VerificationRunCreate,
    VerificationRunDetail,
    VerificationRunResponse,
)
from app.services.verification import engine as verification_engine

router = APIRouter(prefix="/api/projects", tags=["verification"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_project_access(project_id: str, db: Session, current_user: User) -> None:
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse.")


def _get_run_or_404(run_id: str, project_id: str, db: Session) -> VerificationRun:
    run = get_run_by_id(db, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run de verification introuvable."
        )
    return run


def _get_gap_or_404(gap_id: str, run_id: str, db: Session) -> Gap:
    gap = get_gap_by_id(db, gap_id)
    if not gap or gap.run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ecart introuvable."
        )
    return gap


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/verification-runs",
    response_model=VerificationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_verification_run(
    project_id: str,
    payload: VerificationRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VerificationRun:
    """Declenche une nouvelle verification croisee et retourne le run cree.

    Le run passe en statut 'running' immediatement puis 'done' ou 'error'
    en fin de traitement (synchrone en V1 — asynchrone en V2 avec Celery).
    """
    _check_project_access(project_id, db, current_user)

    # Verification que l'export CANECO appartient bien au projet
    from app.repositories import caneco_repository
    export = caneco_repository.get_export(db, payload.caneco_export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export CANECO introuvable pour ce projet.",
        )

    run = verification_engine.run_verification(
        db=db,
        project_id=project_id,
        caneco_export_id=payload.caneco_export_id,
        bordereau_import_id=payload.bordereau_import_id,
        cps_import_id=payload.cps_import_id,
        triggered_by="manual",
        created_by_id=current_user.id,
        icc_presumed_ka=payload.icc_presumed_ka,
    )
    return run


@router.get(
    "/{project_id}/verification-runs",
    response_model=list[VerificationRunResponse],
)
async def list_verification_runs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[VerificationRun]:
    """Liste tous les runs de verification d'un projet."""
    _check_project_access(project_id, db, current_user)
    return get_runs_for_project(db, project_id)


@router.get(
    "/{project_id}/verification-runs/{run_id}",
    response_model=VerificationRunDetail,
)
async def get_verification_run(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Retourne un run avec tous ses ecarts."""
    _check_project_access(project_id, db, current_user)
    run = _get_run_or_404(run_id, project_id, db)
    gaps = get_gaps_for_run(db, run_id)
    return {**run.__dict__, "gaps": gaps}


@router.delete(
    "/{project_id}/verification-runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_verification_run(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Supprime un run et tous ses ecarts."""
    _check_project_access(project_id, db, current_user)
    run = _get_run_or_404(run_id, project_id, db)
    verification_repository.delete_run(db, run)


# ---------------------------------------------------------------------------
# Gaps
# ---------------------------------------------------------------------------


@router.get(
    "/{project_id}/verification-runs/{run_id}/gaps",
    response_model=list[GapResponse],
)
async def list_gaps(
    project_id: str,
    run_id: str,
    severity: str | None = Query(None),
    gap_status: str | None = Query(None, alias="status"),
    code: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Gap]:
    """Liste les ecarts d'un run avec filtres optionnels."""
    _check_project_access(project_id, db, current_user)
    _get_run_or_404(run_id, project_id, db)
    return get_gaps_for_run(db, run_id, severity=severity, status=gap_status, code=code)


@router.patch(
    "/{project_id}/verification-runs/{run_id}/gaps/{gap_id}",
    response_model=GapResponse,
)
async def update_gap(
    project_id: str,
    run_id: str,
    gap_id: str,
    payload: GapStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Gap:
    """Met a jour le statut d'un ecart (acquitter, justifier, clore)."""
    _check_project_access(project_id, db, current_user)
    _get_run_or_404(run_id, project_id, db)
    gap = _get_gap_or_404(gap_id, run_id, db)

    allowed_statuses = {"ouvert", "acquitte", "justifie", "clos"}
    if payload.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Statut invalide. Valeurs acceptees : {', '.join(sorted(allowed_statuses))}.",
        )

    return update_gap_status(
        db,
        gap,
        status=payload.status,
        comment=payload.comment,
        resolved_by_id=current_user.id,
    )
