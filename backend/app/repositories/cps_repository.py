"""Repository CRUD pour les imports CPS."""

from sqlalchemy.orm import Session

from app.models.cps import CpsImport


def get_all(db: Session, project_id: str) -> list[CpsImport]:
    return (
        db.query(CpsImport)
        .filter(CpsImport.project_id == project_id)
        .order_by(CpsImport.created_at.desc())
        .all()
    )


def get_by_id(db: Session, import_id: str) -> CpsImport | None:
    return db.query(CpsImport).filter(CpsImport.id == import_id).first()


def delete(db: Session, imp: CpsImport) -> None:
    db.delete(imp)
    db.commit()
