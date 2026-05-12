"""Service d'upload et de parsing des bordereaux de prix."""

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.orm import Session

from app.models.bordereau import BordereauImport
from app.repositories import bordereau_repository
from app.services.bordereau.parser import detect_indice_from_filename, parse_bordereau_file

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo

_ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}

_ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "application/zip",
}

_UPLOAD_ROOT = Path("/app/data/uploads")


def _validate_file(file: UploadFile) -> None:
    """Verifie le nom, l'extension et le type MIME du fichier upload."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nom de fichier manquant.",
        )
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format non supporte : {suffix}. Le bordereau doit etre en .xlsx.",
        )
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _ALLOWED_MIME_TYPES:
        logger.warning(f"Type MIME inattendu : {content_type} pour {file.filename}")


def _save_file(file: UploadFile, project_id: str) -> tuple[Path, int]:
    """Sauvegarde le fichier sur disque et retourne (chemin absolu, taille)."""
    dest_dir = _UPLOAD_ROOT / project_id / "bordereau"
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{ts}_{file.filename or 'bordereau'}"
    dest_path = dest_dir / file_name

    size = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = file.file.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_FILE_SIZE:
                dest_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Fichier trop volumineux (max 50 Mo).",
                )
            out.write(chunk)

    return dest_path, size


def upload_and_parse(
    db: Session,
    project_id: str,
    user_id: str,
    file: UploadFile,
    indice: str | None = None,
    sheet_name: str | None = None,
) -> BordereauImport:
    """Upload le fichier, parse la feuille CFO et persiste les donnees.

    Le parsing est synchrone pour la V1 (la taille des fichiers bordereau est
    generalement inferieure a 200 lignes, donc < 1 seconde).
    """
    _validate_file(file)
    dest_path, _size = _save_file(file, project_id)

    detected_indice = indice or detect_indice_from_filename(file.filename or "")

    imp = BordereauImport(
        project_id=project_id,
        file_name=file.filename or "bordereau.xlsx",
        file_path=str(dest_path.relative_to(_UPLOAD_ROOT.parent)),
        indice=detected_indice,
        sheet_name=sheet_name,
        status="parsing",
        created_by_id=user_id,
    )
    db.add(imp)
    db.flush()  # obtenir imp.id avant le parsing

    try:
        result = parse_bordereau_file(dest_path, imp.id, sheet_name=sheet_name)

        for section in result.sections:
            db.add(section)
        db.flush()

        for line in result.lines:
            db.add(line)

        imp.status = "parsed"
        imp.total_lines = result.total_lines
        imp.total_articles = result.total_articles
        imp.sections_count = result.sections_count
        imp.sheet_name = result.sheet_name_used
        imp.updated_at = datetime.utcnow()

    except Exception as exc:
        logger.error(f"Erreur parsing bordereau {imp.id} : {exc}")
        imp.status = "error"
        imp.error_message = str(exc)[:500]
        imp.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(imp)
    return imp
