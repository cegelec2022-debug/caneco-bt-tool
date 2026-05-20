"""Controle d'acces aux projets, factorise pour eviter la duplication.

Distinction entre :
- ``ensure_project_access_read`` : autorise ADMIN / RA / BE proprietaire,
  ainsi que CHEF_CHANTIER pour lui permettre de consulter le carnet et y
  saisir les longueurs reelles (Module B).
- ``ensure_project_access_write_studies`` : restreint a ADMIN / RA / BE
  proprietaire — utilise pour les uploads et modifications du dossier d'etudes
  (CANECO, bordereau, CPS, verifications). Le CHEF_CHANTIER n'y a pas acces.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User, UserRole
from app.repositories import project_repository


def _load_or_404(db: Session, project_id: str) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable."
        )
    return project


def ensure_project_access_read(
    db: Session, project_id: str, current_user: User
) -> Project:
    """Acces lecture + saisie chantier. ADMIN / RA / CHEF / BE proprietaire."""
    project = _load_or_404(db, project_id)
    if current_user.role in (UserRole.ADMIN, UserRole.RA, UserRole.CHEF_CHANTIER):
        return project
    if project.created_by == current_user.id:
        return project
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse.")


def ensure_project_access_write_studies(
    db: Session, project_id: str, current_user: User
) -> Project:
    """Acces ecriture sur le dossier d'etudes. ADMIN / RA / BE proprietaire."""
    project = _load_or_404(db, project_id)
    if current_user.role in (UserRole.ADMIN, UserRole.RA):
        return project
    if project.created_by == current_user.id:
        return project
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse.")
