"""Acces aux donnees pour les bordereaux de prix."""

import math

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.bordereau import BordereauImport, BordereauLine, BordereauSection


def get_import(db: Session, import_id: str) -> BordereauImport | None:
    return db.query(BordereauImport).filter(BordereauImport.id == import_id).first()


def list_for_project(db: Session, project_id: str) -> list[BordereauImport]:
    return (
        db.query(BordereauImport)
        .filter(BordereauImport.project_id == project_id)
        .order_by(BordereauImport.created_at.desc())
        .all()
    )


def list_sections(db: Session, import_id: str) -> list[BordereauSection]:
    return (
        db.query(BordereauSection)
        .filter(BordereauSection.bordereau_import_id == import_id)
        .order_by(BordereauSection.order_index)
        .all()
    )


def count_lines(
    db: Session,
    import_id: str,
    section_code: str = "",
    search: str = "",
) -> int:
    q = db.query(func.count(BordereauLine.id)).filter(
        BordereauLine.bordereau_import_id == import_id
    )
    if section_code:
        q = q.join(BordereauSection, BordereauLine.section_id == BordereauSection.id).filter(
            BordereauSection.code == section_code
        )
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                BordereauLine.num_prix.ilike(term),
                BordereauLine.designation.ilike(term),
                BordereauLine.sous_famille.ilike(term),
            )
        )
    result = q.scalar()
    return result or 0


def paginate_lines(
    db: Session,
    import_id: str,
    page: int = 1,
    per_page: int = 50,
    section_code: str = "",
    search: str = "",
) -> list[BordereauLine]:
    q = db.query(BordereauLine).filter(BordereauLine.bordereau_import_id == import_id)
    if section_code:
        q = q.join(BordereauSection, BordereauLine.section_id == BordereauSection.id).filter(
            BordereauSection.code == section_code
        )
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                BordereauLine.num_prix.ilike(term),
                BordereauLine.designation.ilike(term),
                BordereauLine.sous_famille.ilike(term),
            )
        )
    offset = (page - 1) * per_page
    return q.order_by(BordereauLine.excel_row_number).offset(offset).limit(per_page).all()


def get_all_lines(db: Session, import_id: str) -> list[BordereauLine]:
    return (
        db.query(BordereauLine)
        .filter(BordereauLine.bordereau_import_id == import_id)
        .order_by(BordereauLine.excel_row_number)
        .all()
    )


def update_indice(db: Session, imp: BordereauImport, indice: str) -> BordereauImport:
    imp.indice = indice
    db.commit()
    db.refresh(imp)
    return imp


def delete_import(db: Session, imp: BordereauImport) -> None:
    db.delete(imp)
    db.commit()
