"""Service d'upload et de parsing des exports CANECO BT."""

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.orm import Session

from app.models.caneco import CanecoExport
from app.repositories import caneco_repository
from app.services.caneco.parser import detect_indice_from_filename, parse_caneco_file

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo

_ALLOWED_EXTENSIONS = {".xls", ".xlsx", ".xlsm"}

_ALLOWED_MIME_TYPES = {
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
    "application/zip",
}

_UPLOAD_ROOT = Path("/app/data/uploads")


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nom de fichier manquant.",
        )
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format non supporté : {suffix}. Utilisez .xls ou .xlsx.",
        )
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _ALLOWED_MIME_TYPES:
        logger.warning(f"Type MIME inattendu : {content_type} pour {file.filename}")


def _save_file(file: UploadFile, project_id: str) -> tuple[Path, int]:
    dest_dir = _UPLOAD_ROOT / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{ts}_{file.filename or 'caneco'}"
    dest_path = dest_dir / file_name

    size = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = file.file.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_FILE_SIZE:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Fichier trop volumineux (max {_MAX_FILE_SIZE // 1024 // 1024} Mo).",
                )
            out.write(chunk)

    return dest_path, size


def auto_detect_indice(filename: str) -> str | None:
    """Détecte l'indice de révision depuis le nom du fichier uploadé."""
    return detect_indice_from_filename(filename)


def upload_and_parse(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    file: UploadFile,
    indice: str,
) -> CanecoExport:
    """Valide, sauvegarde et parse un export CANECO BT.

    Retourne l'objet CanecoExport créé avec statut final.
    """
    _validate_file(file)

    dest_path, _size = _save_file(file, project_id)
    logger.info(
        f"Fichier CANECO sauvegardé : {dest_path} "
        f"(projet={project_id}, user={user_id}, indice={indice})"
    )

    export = caneco_repository.create_export(
        db,
        project_id=project_id,
        indice=indice,
        file_name=file.filename or dest_path.name,
        file_path=str(dest_path),
        uploaded_by=user_id,
    )

    try:
        result = parse_caneco_file(dest_path)

        for w in result.warnings:
            logger.warning(f"[CANECO parser] {w}")

        caneco_repository.bulk_create_lines(db, export.id, result.lines)
        export = caneco_repository.set_export_done(
            db,
            export,
            line_count=len(result.lines),
            lines_read=result.lines_read,
            columns_detected=result.columns_detected,
            columns_mapped=result.columns_mapped,
            extra_columns_count=result.extra_columns_count,
        )

        logger.info(
            f"Export CANECO {export.id} parsé : {export.line_count} lignes, "
            f"{result.columns_mapped}/{result.columns_detected} colonnes (indice {indice})"
        )

    except (ValueError, Exception) as exc:
        logger.error(f"Erreur parsing CANECO {export.id} : {exc}")
        caneco_repository.set_export_error(db, export)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors du parsing du fichier CANECO : {exc}",
        ) from exc

    return export
