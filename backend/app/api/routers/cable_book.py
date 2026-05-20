"""Endpoints carnet de cables — agregation et export Excel."""

from __future__ import annotations

from urllib.parse import quote as urlquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.caneco import CanecoLine
from app.models.user import User, UserRole
from app.repositories import caneco_repository, project_repository
from app.schemas.cable_book import CableBookEntryResponse, CableBookReportResponse
from app.services.cable_book.builder import CableBookEntry, build_cable_book
from app.services.cable_book.excel_exporter import build_cable_book_workbook

router = APIRouter(prefix="/api/projects", tags=["cable-book"])


def _check_project_access(project_id: str, db: Session, current_user: User) -> None:
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable."
        )
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse."
            )


def _entry_to_response(entry: CableBookEntry) -> CableBookEntryResponse:
    """Convertit une CableBookEntry interne en schema Pydantic."""
    return CableBookEntryResponse(
        type_cable=entry.type_cable,
        cable_caneco=entry.cable_caneco,
        section_mm2=entry.section_mm2,
        nb_conducteurs=entry.nb_conducteurs,
        nb_circuits_paralleles=entry.nb_circuits_paralleles,
        longueur_totale_m=round(entry.longueur_totale_m, 2),
        nb_occurrences=entry.nb_occurrences,
        pourcentage_du_total=round(entry.pourcentage_du_total, 2),
        reperes_aval=sorted(entry.reperes_aval),
        longueurs_par_aval={k: round(v, 2) for k, v in entry.longueurs_par_aval.items()},
        ame=entry.ame,
    )


@router.get(
    "/{project_id}/cable-book",
    response_model=CableBookReportResponse,
)
def get_cable_book(
    project_id: str,
    caneco_export_id: str = Query(..., description="ID de l'export CANECO source"),
    repere_aval: str | None = Query(
        None,
        description="Filtre optionnel : ne garde que les cables d'un tableau aval donne",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CableBookReportResponse:
    """Retourne le carnet de cables aggregre pour un export CANECO donne."""
    _check_project_access(project_id, db, current_user)

    export = caneco_repository.get_export(db, caneco_export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export CANECO introuvable pour ce projet.",
        )

    lines: list[CanecoLine] = (
        db.query(CanecoLine).filter(CanecoLine.export_id == caneco_export_id).all()
    )

    report = build_cable_book(lines, filter_repere_aval=repere_aval)

    return CableBookReportResponse(
        entries=[_entry_to_response(e) for e in report.entries],
        longueur_totale_projet_m=round(report.longueur_totale_projet_m, 2),
        nb_lignes_caneco_traitees=report.nb_lignes_caneco_traitees,
        nb_types_cables_distincts=report.nb_types_cables_distincts,
        longueur_par_type_cable={
            k: round(v, 2) for k, v in report.longueur_par_type_cable.items()
        },
        longueur_par_aval={
            k: round(v, 2) for k, v in report.longueur_par_aval.items()
        },
        top5=[_entry_to_response(e) for e in report.top5],
    )


@router.get("/{project_id}/cable-book/export.xlsx")
def export_cable_book_xlsx(
    project_id: str,
    caneco_export_id: str = Query(..., description="ID de l'export CANECO source"),
    repere_aval: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Telecharge le carnet de cables au format Excel (feuilles Sommaire + Rapport)."""
    _check_project_access(project_id, db, current_user)

    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable."
        )

    export = caneco_repository.get_export(db, caneco_export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export CANECO introuvable pour ce projet.",
        )

    lines: list[CanecoLine] = (
        db.query(CanecoLine).filter(CanecoLine.export_id == caneco_export_id).all()
    )
    report = build_cable_book(lines, filter_repere_aval=repere_aval)

    content = build_cable_book_workbook(
        report,
        project_name=project.name,
        project_code=project.code,
        indice=export.indice or "",
    )

    filename = f"carnet-cables_{project.code}_{export.indice or 'export'}.xlsx"
    # RFC 5987 : encode le filename pour les caracteres non-ASCII
    encoded = urlquote(filename)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded}",
        },
    )
