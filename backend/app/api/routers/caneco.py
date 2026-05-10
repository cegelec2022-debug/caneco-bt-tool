import math

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.ratelimit import limiter
from app.models.caneco import CanecoExport
from app.models.user import User, UserRole
from app.repositories import caneco_repository, project_repository
from app.schemas.caneco import CanecoExportDetail, CanecoExportResponse, CanecoLineResponse
from app.services.caneco import excel_export as caneco_excel
from app.services.caneco import service as caneco_service

router = APIRouter(prefix="/api/projects", tags=["caneco"])


def _check_project_access(project_id: str, db: Session, current_user: User) -> None:
    """Vérifie que le projet existe et que l'utilisateur y a accès."""
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")


def _get_export_or_404(export_id: str, project_id: str, db: Session) -> CanecoExport:
    export = caneco_repository.get_export(db, export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export introuvable."
        )
    return export


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/caneco/upload",
    response_model=CanecoExportResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def upload_caneco(
    request: Request,
    project_id: str,
    file: UploadFile,
    indice: str = Form(default="A"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CanecoExportResponse:
    """Upload et parse un export CANECO BT (XLS/XLSX)."""
    indice = indice.strip().upper() or "A"
    _check_project_access(project_id, db, current_user)

    export = caneco_service.upload_and_parse(
        db,
        project_id=project_id,
        user_id=current_user.id,
        file=file,
        indice=indice,
    )
    return CanecoExportResponse.model_validate(export)


@router.get(
    "/{project_id}/caneco",
    response_model=list[CanecoExportResponse],
)
def list_exports(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CanecoExportResponse]:
    """Liste tous les exports CANECO d'un projet."""
    _check_project_access(project_id, db, current_user)
    exports = caneco_repository.list_for_project(db, project_id)
    return [CanecoExportResponse.model_validate(e) for e in exports]


@router.get(
    "/{project_id}/caneco/{export_id}",
    response_model=CanecoExportDetail,
)
def get_export_detail(
    project_id: str,
    export_id: str,
    page: int = 1,
    per_page: int = 50,
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CanecoExportDetail:
    """Retourne les lignes paginées d'un export CANECO, avec recherche full-text optionnelle."""
    _check_project_access(project_id, db, current_user)
    export = _get_export_or_404(export_id, project_id, db)

    page = max(1, page)
    per_page = max(1, min(200, per_page))

    total = caneco_repository.count_lines(db, export_id, search=search)
    lines = caneco_repository.paginate_lines(
        db, export_id, page=page, per_page=per_page, search=search
    )
    total_pages = max(1, math.ceil(total / per_page))

    return CanecoExportDetail(
        export=CanecoExportResponse.model_validate(export),
        lines=[CanecoLineResponse.model_validate(ln) for ln in lines],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.patch(
    "/{project_id}/caneco/{export_id}/indice",
    response_model=CanecoExportResponse,
)
def update_indice(
    project_id: str,
    export_id: str,
    indice: str = Form(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CanecoExportResponse:
    """Met à jour l'indice de révision d'un export CANECO."""
    _check_project_access(project_id, db, current_user)
    export = _get_export_or_404(export_id, project_id, db)
    indice = indice.strip().upper()
    if not indice:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'indice ne peut pas être vide.",
        )
    export = caneco_repository.update_indice(db, export, indice)
    return CanecoExportResponse.model_validate(export)


@router.get(
    "/{project_id}/caneco/{export_id}/export-excel",
    response_class=StreamingResponse,
)
def export_excel(
    project_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Exporte toutes les lignes parsées en fichier Excel (.xlsx) avec en-têtes bleu VINCI."""
    _check_project_access(project_id, db, current_user)
    export = _get_export_or_404(export_id, project_id, db)

    lines = caneco_repository.get_all_lines(db, export_id)
    buffer = caneco_excel.export_to_xlsx(lines, export.file_name, export.indice)

    safe_name = export.file_name.replace(" ", "_").rstrip(".xls").rstrip(".xlsx")
    filename = f"CANECO_Indice_{export.indice}_{safe_name}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{project_id}/caneco/{export_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_export(
    project_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Supprime un export CANECO et toutes ses lignes."""
    _check_project_access(project_id, db, current_user)
    export = _get_export_or_404(export_id, project_id, db)
    caneco_repository.delete_export(db, export)
