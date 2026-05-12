"""Endpoints CPS — Cahier des Prescriptions Speciales."""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter
from app.models.cps import CpsImport
from app.models.user import User, UserRole
from app.repositories import cps_repository, project_repository
from app.schemas.cps import CpsImportDetail, CpsImportResponse, CpsRuleItem
from app.services.cps import service as cps_service

router = APIRouter(prefix="/api/projects", tags=["cps"])


def _check_project_access(project_id: str, db: Session, current_user: User) -> None:
    """Verifie que le projet existe et que l'utilisateur y a acces."""
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse.")


def _get_import_or_404(import_id: str, project_id: str, db: Session) -> CpsImport:
    imp = cps_repository.get_by_id(db, import_id)
    if not imp or imp.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Import CPS introuvable."
        )
    return imp


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/cps-imports",
    response_model=CpsImportResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def upload_cps(
    request: Request,
    project_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CpsImport:
    """Upload un PDF CPS, parse les regles et retourne l'import cree."""
    _check_project_access(project_id, db, current_user)
    return cps_service.upload_and_parse(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        file=file,
    )


@router.get(
    "/{project_id}/cps-imports",
    response_model=list[CpsImportResponse],
)
async def list_cps_imports(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CpsImport]:
    """Liste les imports CPS d'un projet."""
    _check_project_access(project_id, db, current_user)
    return cps_repository.get_all(db, project_id)


@router.get(
    "/{project_id}/cps-imports/{import_id}",
    response_model=CpsImportDetail,
)
async def get_cps_import(
    project_id: str,
    import_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Retourne un import CPS avec la liste complete des regles extraites."""
    _check_project_access(project_id, db, current_user)
    imp = _get_import_or_404(import_id, project_id, db)

    rules: list[CpsRuleItem] = []
    if imp.extracted_rules:
        rules = [CpsRuleItem(**r) for r in imp.extracted_rules]

    return {"imp": imp, "rules": rules}


@router.delete(
    "/{project_id}/cps-imports/{import_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cps_import(
    project_id: str,
    import_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Supprime un import CPS."""
    _check_project_access(project_id, db, current_user)
    imp = _get_import_or_404(import_id, project_id, db)
    cps_repository.delete(db, imp)
