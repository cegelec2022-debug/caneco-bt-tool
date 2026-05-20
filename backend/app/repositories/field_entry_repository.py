"""Acces donnees aux saisies chantier (Module B)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.caneco import CanecoLine
from app.models.field_entry import FieldEntry


def get_by_caneco_line(db: Session, caneco_line_id: str) -> FieldEntry | None:
    return (
        db.query(FieldEntry)
        .filter(FieldEntry.caneco_line_id == caneco_line_id)
        .first()
    )


def list_for_project(db: Session, project_id: str) -> list[FieldEntry]:
    """Toutes les saisies chantier d'un projet (via jointure CanecoLine -> CanecoExport)."""
    from app.models.caneco import CanecoExport

    return (
        db.query(FieldEntry)
        .join(CanecoLine, CanecoLine.id == FieldEntry.caneco_line_id)
        .join(CanecoExport, CanecoExport.id == CanecoLine.export_id)
        .filter(CanecoExport.project_id == project_id)
        .all()
    )


def list_for_export(db: Session, caneco_export_id: str) -> list[FieldEntry]:
    """Saisies chantier d'un export CANECO precis."""
    return (
        db.query(FieldEntry)
        .join(CanecoLine, CanecoLine.id == FieldEntry.caneco_line_id)
        .filter(CanecoLine.export_id == caneco_export_id)
        .all()
    )


def upsert(
    db: Session,
    *,
    caneco_line_id: str,
    longueur_realisee: float,
    commentaire: str | None,
    user_id: str,
) -> FieldEntry:
    """Cree ou met a jour la saisie chantier d'une ligne CANECO.

    Une seule saisie par ligne CANECO : si elle existe, on met a jour les
    valeurs (longueur, commentaire, auteur). L'auteur reflete la derniere
    personne qui a modifie la saisie.
    """
    entry = get_by_caneco_line(db, caneco_line_id)
    if entry is None:
        entry = FieldEntry(
            caneco_line_id=caneco_line_id,
            longueur_realisee=longueur_realisee,
            commentaire=commentaire,
            saisi_par=user_id,
        )
        db.add(entry)
    else:
        entry.longueur_realisee = longueur_realisee
        entry.commentaire = commentaire
        entry.saisi_par = user_id
    db.commit()
    db.refresh(entry)
    return entry


def delete(db: Session, entry: FieldEntry) -> None:
    db.delete(entry)
    db.commit()
