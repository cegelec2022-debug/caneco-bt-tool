import json
import uuid
from typing import Any

from sqlalchemy import or_
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
    *,
    line_count: int,
    lines_read: int,
    columns_detected: int,
    columns_mapped: int,
    extra_columns_count: int,
    status: str = "parsed",
) -> CanecoExport:
    export.line_count = line_count
    export.lines_read = lines_read
    export.columns_detected = columns_detected
    export.columns_mapped = columns_mapped
    export.extra_columns_count = extra_columns_count
    export.status = status
    db.commit()
    db.refresh(export)
    return export


def set_export_error(db: Session, export: CanecoExport) -> CanecoExport:
    export.status = "error"
    db.commit()
    db.refresh(export)
    return export


def update_indice(db: Session, export: CanecoExport, indice: str) -> CanecoExport:
    export.indice = indice
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
            excel_row_number=line.excel_row_number,
            row_index=line.row_index,
            amont=line.amont,
            repere_aval=line.repere_aval,
            repere=line.repere,
            designation=line.designation,
            style=line.style,
            nb_recepteurs=line.nb_recepteurs,
            consommation=line.consommation,
            ib=line.ib,
            longueur=line.longueur,
            type_cable=line.type_cable,
            nb_cables_multi=line.nb_cables_multi,
            cable=line.cable,
            neutre=line.neutre,
            pe=line.pe,
            calibre=line.calibre,
            bloc_coupure=line.bloc_coupure,
            bloc_declencheur=line.bloc_declencheur,
            bloc_differentiel=line.bloc_differentiel,
            ir_th_in=line.ir_th_in,
            ir_mg_in=line.ir_mg_in,
            icu=line.icu,
            contacteur=line.contacteur,
            ame=line.ame,
            raw_data=json.dumps(line.raw_data, ensure_ascii=False) if line.raw_data else None,
            extra_columns=(
                json.dumps(line.extra_columns, ensure_ascii=False) if line.extra_columns else None
            ),
        )
        for line in parsed_lines
    ]
    db.bulk_save_objects(objects)
    db.commit()


def get_all_lines(db: Session, export_id: str) -> list[CanecoLine]:
    """Retourne toutes les lignes d'un export, sans pagination, ordonnées par ligne Excel."""
    return (
        db.query(CanecoLine)
        .filter(CanecoLine.export_id == export_id)
        .order_by(CanecoLine.excel_row_number)
        .all()
    )


def count_lines(db: Session, export_id: str, search: str = "") -> int:
    q = db.query(CanecoLine).filter(CanecoLine.export_id == export_id)
    if search:
        q = _apply_search(q, search)
    return q.count()


def paginate_lines(
    db: Session,
    export_id: str,
    page: int = 1,
    per_page: int = 50,
    search: str = "",
) -> list[CanecoLine]:
    offset = (page - 1) * per_page
    q = (
        db.query(CanecoLine)
        .filter(CanecoLine.export_id == export_id)
        .order_by(CanecoLine.excel_row_number)
    )
    if search:
        q = _apply_search(q, search)
    return q.offset(offset).limit(per_page).all()


def _apply_search(q: Any, search: str) -> Any:
    """Filtre full-text sur les champs texte principaux."""
    term = f"%{search}%"
    return q.filter(
        or_(
            CanecoLine.repere.ilike(term),
            CanecoLine.designation.ilike(term),
            CanecoLine.style.ilike(term),
            CanecoLine.amont.ilike(term),
            CanecoLine.repere_aval.ilike(term),
            CanecoLine.type_cable.ilike(term),
            CanecoLine.cable.ilike(term),
            CanecoLine.bloc_coupure.ilike(term),
            CanecoLine.bloc_declencheur.ilike(term),
            CanecoLine.consommation.ilike(term),
        )
    )


def delete_export(db: Session, export: CanecoExport) -> None:
    db.delete(export)
    db.commit()
