import json
import uuid

from sqlalchemy.orm import Session

from app.models.caneco import CanecoExport, CanecoLine
from app.services.caneco.parser import ParsedLine


def list_for_project(db: Session, project_id: str) -> list[CanecoExport]:
    return (
        db.query(CanecoExport)
        .filter(CanecoExport.project_id == project_id)
        .order_by(CanecoExport.uploaded_at.desc())
        .all()
    )


def get_export(db: Session, export_id: str) -> CanecoExport | None:
    return db.query(CanecoExport).filter(CanecoExport.id == export_id).first()


def create_export(
    db: Session,
    *,
    project_id: str,
    indice: str,
    file_name: str,
    file_path: str | None,
    uploaded_by: str,
    status: str = "parsing",
) -> CanecoExport:
    export = CanecoExport(
        project_id=project_id,
        indice=indice,
        file_name=file_name,
        file_path=file_path,
        status=status,
        uploaded_by=uploaded_by,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


def set_export_done(
    db: Session,
    export: CanecoExport,
    line_count: int,
    status: str = "parsed",
) -> CanecoExport:
    export.line_count = line_count
    export.status = status
    db.commit()
    db.refresh(export)
    return export


def set_export_error(db: Session, export: CanecoExport) -> CanecoExport:
    export.status = "error"
    db.commit()
    db.refresh(export)
    return export


def bulk_create_lines(
    db: Session,
    export_id: str,
    parsed_lines: list[ParsedLine],
) -> None:
    """Insère toutes les lignes en une seule transaction."""
    objects = [
        CanecoLine(
            id=str(uuid.uuid4()),
            export_id=export_id,
            row_index=line.row_index,
            repere=line.repere,
            designation=line.designation,
            style=line.style,
            nb_recepteurs=line.nb_recepteurs,
            consommation=line.consommation,
            ib=line.ib,
            longueur=line.longueur,
            type_cable=line.type_cable,
            cable=line.cable,
            neutre=line.neutre,
            pe=line.pe,
            ame=line.ame,
            calibre=line.calibre,
            bloc_coupure=line.bloc_coupure,
            bloc_declencheur=line.bloc_declencheur,
            bloc_differentiel=line.bloc_differentiel,
            ir_th_in=line.ir_th_in,
            ir_mg_in=line.ir_mg_in,
            icu=line.icu,
            extra_data=json.dumps(line.extra_data, ensure_ascii=False) if line.extra_data else None,
        )
        for line in parsed_lines
    ]
    db.bulk_save_objects(objects)
    db.commit()


def count_lines(db: Session, export_id: str) -> int:
    return db.query(CanecoLine).filter(CanecoLine.export_id == export_id).count()


def paginate_lines(
    db: Session,
    export_id: str,
    page: int = 1,
    per_page: int = 50,
) -> list[CanecoLine]:
    offset = (page - 1) * per_page
    return (
        db.query(CanecoLine)
        .filter(CanecoLine.export_id == export_id)
        .order_by(CanecoLine.row_index)
        .offset(offset)
        .limit(per_page)
        .all()
    )


def delete_export(db: Session, export: CanecoExport) -> None:
    db.delete(export)
    db.commit()
