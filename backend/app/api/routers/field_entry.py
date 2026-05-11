"""Endpoints saisie chantier (Module B).

Le Chef de Chantier remonte les longueurs reellement tirees sur chaque depart.
La saisie est UNIQUE par ligne CANECO : un PUT recree ou met a jour.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.caneco import CanecoExport, CanecoLine
from app.models.user import User, UserRole
from app.repositories import (
    caneco_repository,
    field_entry_repository,
    project_repository,
)
from app.schemas.field_entry import (
    ECART_COMMENT_REQUIRED_PCT,
    FieldEntryResponse,
    FieldEntryUpsert,
    commentaire_obligatoire,
)

router = APIRouter(prefix="/api/projects", tags=["field-entries"])


def _check_project_access_chantier(
    project_id: str, db: Session, current_user: User
):
    """Verifie l'acces a un projet pour les operations de saisie chantier.

    - ADMIN / RA : voient et saisissent sur tous les projets.
    - CHEF_CHANTIER : peut saisir sur tous les projets actifs (gestion fine
      des assignations chantier renvoyee a V2).
    - BE : voit et saisit uniquement sur les projets qu'il a crees.
    """
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable."
        )
    if current_user.role in (UserRole.ADMIN, UserRole.RA, UserRole.CHEF_CHANTIER):
        return project
    if project.created_by == current_user.id:
        return project
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse.")


def _check_line_belongs_to_project(
    db: Session, caneco_line_id: str, project_id: str
) -> CanecoLine:
    """Recharge la ligne CANECO et verifie qu'elle appartient bien au projet.

    Garde-fou securite : on ne se fie pas a un caneco_line_id du body sans
    valider qu'il est dans le projet sur lequel l'utilisateur est autorise.
    """
    line = db.query(CanecoLine).filter(CanecoLine.id == caneco_line_id).first()
    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ligne CANECO introuvable."
        )
    export = caneco_repository.get_export(db, line.export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette ligne CANECO n'appartient pas au projet.",
        )
    return line


@router.put(
    "/{project_id}/field-entries/{caneco_line_id}",
    response_model=FieldEntryResponse,
)
def upsert_field_entry(
    project_id: str,
    caneco_line_id: str,
    payload: FieldEntryUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FieldEntryResponse:
    """Cree ou met a jour la saisie chantier d'un depart (ligne CANECO)."""
    _check_project_access_chantier(project_id, db, current_user)
    line = _check_line_belongs_to_project(db, caneco_line_id, project_id)

    # Regle metier : commentaire obligatoire si reel=0 ou ecart > 50 % du prevu.
    if commentaire_obligatoire(line.longueur, payload.longueur_realisee) and not (
        payload.commentaire and payload.commentaire.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Commentaire obligatoire : l'ecart depasse "
                f"{ECART_COMMENT_REQUIRED_PCT:.0f} % de la longueur prevue, "
                "ou la longueur reelle est nulle. Justifiez la situation pour "
                "que le BE et le RA en soient informes."
            ),
        )

    entry = field_entry_repository.upsert(
        db,
        caneco_line_id=caneco_line_id,
        longueur_realisee=payload.longueur_realisee,
        commentaire=payload.commentaire,
        user_id=current_user.id,
    )
    return FieldEntryResponse.model_validate(entry)


@router.delete(
    "/{project_id}/field-entries/{caneco_line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_field_entry(
    project_id: str,
    caneco_line_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime la saisie chantier d'un depart (annule la saisie)."""
    _check_project_access_chantier(project_id, db, current_user)
    _check_line_belongs_to_project(db, caneco_line_id, project_id)

    entry = field_entry_repository.get_by_caneco_line(db, caneco_line_id)
    if entry is not None:
        field_entry_repository.delete(db, entry)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_id}/field-entries",
    response_model=list[FieldEntryResponse],
)
def list_field_entries(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FieldEntryResponse]:
    """Liste toutes les saisies chantier du projet (toutes lignes / tous indices)."""
    _check_project_access_chantier(project_id, db, current_user)
    entries = field_entry_repository.list_for_project(db, project_id)
    return [FieldEntryResponse.model_validate(e) for e in entries]
