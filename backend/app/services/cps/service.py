"""Service d'upload et de parsing des CPS PDF."""

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.orm import Session

from app.models.cps import CpsImport
from app.services.cps.parser import extract_rules

_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 Mo

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}

_UPLOAD_ROOT = Path("/app/data/uploads")


def _validate_file(file: UploadFile) -> None:
    """Verifie le nom et le type MIME du fichier."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nom de fichier manquant.",
        )
    suffix = Path(file.filename).suffix.lower()
    if suffix != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format non supporte : {suffix}. Le CPS doit etre un fichier PDF.",
        )
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _ALLOWED_MIME_TYPES:
        logger.warning(f"Type MIME inattendu : {content_type} pour {file.filename}")


def _save_file(file_content: bytes, project_id: str, import_id: str, file_name: str) -> Path:
    """Sauvegarde le fichier PDF sur disque."""
    dest_dir = _UPLOAD_ROOT / project_id / "cps"
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_cps_{import_id}.pdf"
    dest_path = dest_dir / safe_name
    dest_path.write_bytes(file_content)
    return dest_path


def upload_and_parse(
    db: Session,
    project_id: str,
    user_id: str,
    file: UploadFile,
) -> CpsImport:
    """Upload le fichier CPS, parse les regles et persiste les donnees.

    Le parsing est synchrone (les PDF CPS sont generalement < 50 pages).
    """
    _validate_file(file)

    file_content = file.file.read()
    if len(file_content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 100 Mo).",
        )

    imp = CpsImport(
        project_id=project_id,
        file_name=file.filename or "cps.pdf",
        status="parsing",
        extraction_method="regex_v1",
        created_by_id=user_id,
    )
    db.add(imp)
    db.flush()

    try:
        dest_path = _save_file(file_content, project_id, imp.id, file.filename or "cps.pdf")
        imp.file_path = str(dest_path.relative_to(_UPLOAD_ROOT.parent))

        result = extract_rules(dest_path, use_llm=False)

        imp.status = "parsed"
        imp.page_count = result.page_count
        imp.rules_count = len(result.rules)
        imp.extracted_rules = result.rules

    except Exception as exc:
        logger.error(f"Erreur parsing CPS {imp.id} : {exc}")
        imp.status = "error"
        imp.error_message = str(exc)[:500]

    db.commit()
    db.refresh(imp)
    return imp
