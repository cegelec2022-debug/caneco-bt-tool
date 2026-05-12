"""Endpoints bordereau de prix."""

import math

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter
from app.models.bordereau import BordereauImport
from app.models.user import User, UserRole
from app.repositories import bordereau_repository, project_repository
from app.schemas.bordereau import (
    BordereauDetail,
    BordereauImportResponse,
    BordereauLineResponse,
    BordereauSectionResponse,
    BordereauSheetPreview,
)
from app.services.bordereau import service as bordereau_service
from app.services.bordereau.parser import list_sheet_names

router = APIRouter(prefix="/api/projects", tags=["bordereau"])


def _check_project_access(project_id: str, db: Session, current_user: User) -> None:
    """Verifie que le projet existe et que l'utilisateur y a acces."""
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse.")


def _get_import_or_404(import_id: str, project_id: str, db: Session) -> BordereauImport:
    imp = bordereau_repository.get_import(db, import_id)
    if not imp or imp.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Import bordereau introuvable."
        )
    return imp


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/bordereau/preview-sheets",
    response_model=BordereauSheetPreview,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def preview_sheets(
    request: Request,
    project_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BordereauSheetPreview:
    """Lit les noms de feuilles d'un fichier Excel sans le parser ni le persister.

    Permet au frontend de proposer un choix de feuille avant l'import.
    """
    _check_project_access(project_id, db, current_user)

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier doit etre au format .xlsx.",
        )

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 50 Mo).",
        )

    try:
        sheets, detected = list_sheet_names(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Impossible de lire les feuilles du fichier : {exc}",
        ) from exc

    return BordereauSheetPreview(sheets=sheets, detected=detected)


@router.post(
    "/{project_id}/bordereau/upload",
    response_model=BordereauImportResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def upload_bordereau(
    request: Request,
    project_id: str,
    file: UploadFile,
    indice: str = Form(default=""),
    sheet_name: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BordereauImportResponse:
    """Upload et parse un bordereau de prix.

    sheet_name : nom exact de la feuille a parser (optionnel — auto-detecte si absent).
    """
    indice_val: str | None = indice.strip().upper() or None
    sheet_val: str | None = sheet_name.strip() or None
    _check_project_access(project_id, db, current_user)

    imp = bordereau_service.upload_and_parse(
        db,
        project_id=project_id,
        user_id=current_user.id,
        file=file,
        indice=indice_val,
        sheet_name=sheet_val,
    )
    return BordereauImportResponse.model_validate(imp)


@router.get(
    "/{project_id}/bordereau",
    response_model=list[BordereauImportResponse],
)
def list_imports(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BordereauImportResponse]:
    """Liste tous les imports bordereau d'un projet."""
    _check_project_access(project_id, db, current_user)
    imports = bordereau_repository.list_for_project(db, project_id)
    return [BordereauImportResponse.model_validate(i) for i in imports]


@router.get(
    "/{project_id}/bordereau/{import_id}",
    response_model=BordereauDetail,
)
def get_import_detail(
    project_id: str,
    import_id: str,
    page: int = 1,
    per_page: int = 50,
    section_code: str = "",
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BordereauDetail:
    """Retourne les lignes paginées d'un import bordereau, filtrables par section et par recherche."""
    _check_project_access(project_id, db, current_user)
    imp = _get_import_or_404(import_id, project_id, db)

    page = max(1, page)
    per_page = max(1, min(200, per_page))

    sections = bordereau_repository.list_sections(db, import_id)
    total = bordereau_repository.count_lines(
        db, import_id, section_code=section_code, search=search
    )
    lines = bordereau_repository.paginate_lines(
        db, import_id, page=page, per_page=per_page, section_code=section_code, search=search
    )
    total_pages = max(1, math.ceil(total / per_page))

    return BordereauDetail(
        imp=BordereauImportResponse.model_validate(imp),
        sections=[BordereauSectionResponse.model_validate(s) for s in sections],
        lines=[BordereauLineResponse.model_validate(ln) for ln in lines],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.patch(
    "/{project_id}/bordereau/{import_id}/indice",
    response_model=BordereauImportResponse,
)
def update_indice(
    project_id: str,
    import_id: str,
    indice: str = Form(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BordereauImportResponse:
    """Met a jour l'indice de revision d'un import bordereau."""
    _check_project_access(project_id, db, current_user)
    imp = _get_import_or_404(import_id, project_id, db)
    indice = indice.strip().upper()
    if not indice:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'indice ne peut pas etre vide.",
        )
    updated = bordereau_repository.update_indice(db, imp, indice)
    return BordereauImportResponse.model_validate(updated)


@router.delete(
    "/{project_id}/bordereau/{import_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_import(
    project_id: str,
    import_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Supprime un import bordereau et toutes ses lignes."""
    _check_project_access(project_id, db, current_user)
    imp = _get_import_or_404(import_id, project_id, db)
    bordereau_repository.delete_import(db, imp)
