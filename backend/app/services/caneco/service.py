"""Service d'upload et de parsing des exports CANECO BT."""

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.orm import Session

from app.models.caneco import CanecoExport
from app.repositories import caneco_repository
from app.services.caneco.parser import parse_caneco_file

# Taille max : 50 Mo
_MAX_FILE_SIZE = 50 * 1024 * 1024

_ALLOWED_EXTENSIONS = {".xls", ".xlsx", ".xlsm"}

_ALLOWED_MIME_TYPES = {
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # certains navigateurs pour .xls
    "application/zip",  # .xlsx est un ZIP
}

# Dossier racine des uploads (monté via Docker volume)
_UPLOAD_ROOT = Path("/app/data/uploads")


def _validate_file(file: UploadFile) -> None:
    """Valide l'extension et le type MIME du fichier uploadé."""
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
        logger.warning(
            f"Type MIME inattendu : {content_type} pour {file.filename} — "
            "poursuite de la validation par extension."
        )


def _save_file(file: UploadFile, project_id: str) -> tuple[Path, int]:
    """Sauvegarde le fichier sur disque et retourne (chemin, taille)."""
    dest_dir = _UPLOAD_ROOT / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    suffix = Path(file.filename or "file.xls").suffix.lower()
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


def upload_and_parse(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    file: UploadFile,
    indice: str,
) -> CanecoExport:
    """Valide, sauvegarde et parse un export CANECO BT.

    Args:
        db: Session SQLAlchemy.
        project_id: ID du projet cible.
        user_id: ID de l'utilisateur qui uploade.
        file: Fichier uploadé via FastAPI UploadFile.
        indice: Indice de révision (A, B, B2…).

    Returns:
        L'objet CanecoExport créé avec le statut final.

    Raises:
        HTTPException: En cas de fichier invalide ou d'erreur de parsing.
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

        if result.warnings:
            for w in result.warnings:
                logger.warning(f"[CANECO parser] {w}")

        caneco_repository.bulk_create_lines(db, export.id, result.lines)
        export = caneco_repository.set_export_done(db, export, len(result.lines))

        logger.info(
            f"Export CANECO {export.id} parsé avec succès : "
            f"{export.line_count} lignes (indice {indice})"
        )

    except (ValueError, Exception) as exc:
        logger.error(f"Erreur parsing CANECO {export.id} : {exc}")
        caneco_repository.set_export_error(db, export)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur lors du parsing du fichier CANECO : {exc}",
        ) from exc

    return export
