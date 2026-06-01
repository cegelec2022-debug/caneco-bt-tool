"""Endpoints tableaux electriques (authentifies).

Generation depuis un export CANECO, liste, QR PNG, planche A4 d'etiquettes et
fiche PDF. La fiche publique (non authentifiee) est dans ``routers/public``.

Le QR encode l'URL publique de la fiche. Pour que le scan fonctionne depuis un
telephone (et pas vers localhost), l'origine publique provient en priorite du
parametre ``PUBLIC_BASE_URL`` (configuration serveur — ex. l'URL du tunnel),
sinon de l'origine du navigateur transmise par le front (``base_url``).
"""

from __future__ import annotations

from urllib.parse import quote as urlquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.access import ensure_project_access_read
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.repositories import caneco_repository, project_repository, tableau_repository
from app.schemas.tableau import TableauResponse, TableauxGenerateResponse
from app.services.qr.generator import generate_qr_png
from app.services.qr.pdf import build_fiche_pdf, build_labels_pdf
from app.services.tableau.builder import TableauDerive, derive_tableaux, normalize_repere
from app.services.tableau.fiche import build_fiche_data

router = APIRouter(prefix="/api/projects", tags=["tableaux"])


def _check_project_access_write(project_id: str, db: Session, current_user: User):
    """Generation des tableaux : ADMIN / RA / BE proprietaire (pas le Chef)."""
    project = project_repository.get_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable."
        )
    if current_user.role not in (UserRole.ADMIN, UserRole.RA):
        if project.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse."
            )
    return project


def _check_project_access_read(project_id: str, db: Session, current_user: User):
    """Lecture / impression QR / fiche : ADMIN / RA / CHEF / BE proprietaire.

    Le chef de chantier a besoin de la liste des tableaux pour scanner les
    QR et acceder aux fiches publiques, et d'imprimer les etiquettes sur place.
    """
    return ensure_project_access_read(db, project_id, current_user)


def _public_base(base_url: str | None) -> str:
    """Origine publique a encoder dans le QR.

    Priorite a la configuration serveur ``PUBLIC_BASE_URL`` (ex. URL du tunnel)
    pour que le QR soit scannable depuis un telephone meme si le BE travaille
    sur localhost. Sinon, origine du navigateur transmise par le front.
    """
    configured = (settings.PUBLIC_BASE_URL or "").strip().rstrip("/")
    if configured:
        return configured
    base = (base_url or "").strip().rstrip("/")
    if not (base.startswith("http://") or base.startswith("https://")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Origine publique absente : configurez PUBLIC_BASE_URL.",
        )
    return base


def _derive_map(db: Session, project_id: str) -> dict[str, TableauDerive]:
    """Tableaux derives du dernier export CANECO, indexes par repere normalise."""
    exports = caneco_repository.list_for_project(db, project_id)
    if not exports:
        return {}
    lines = caneco_repository.get_all_lines(db, exports[0].id)
    return {d.cle: d for d in derive_tableaux(lines)}


def _to_response(tab, dmap: dict[str, TableauDerive]) -> TableauResponse:
    d = dmap.get(normalize_repere(tab.repere))
    return TableauResponse(
        id=tab.id,
        repere=tab.repere,
        designation=tab.designation,
        qr_token=tab.qr_token,
        nb_departs=d.nb_departs if d else 0,
        longueur_totale_m=d.longueur_totale_m if d else 0.0,
    )


@router.post(
    "/{project_id}/tableaux/generate",
    response_model=TableauxGenerateResponse,
)
def generate_tableaux(
    project_id: str,
    caneco_export_id: str = Query(..., description="Export CANECO source"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TableauxGenerateResponse:
    """(Re)genere les tableaux d'un projet depuis un export CANECO.

    Idempotent : conserve le qr_token des tableaux deja crees (etiquettes deja
    posees toujours valides).
    """
    _check_project_access_write(project_id, db, current_user)

    export = caneco_repository.get_export(db, caneco_export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export CANECO introuvable pour ce projet.",
        )

    lines = caneco_repository.get_all_lines(db, caneco_export_id)
    derived = derive_tableaux(lines)
    tableaux = tableau_repository.upsert_from_derived(db, project_id, derived)

    dmap = {d.cle: d for d in derived}
    responses = [_to_response(t, dmap) for t in tableaux]
    return TableauxGenerateResponse(
        caneco_indice=export.indice or "—",
        nb_tableaux=len(responses),
        nb_departs_total=sum(r.nb_departs for r in responses),
        tableaux=responses,
    )


@router.get(
    "/{project_id}/tableaux",
    response_model=list[TableauResponse],
)
def list_tableaux(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TableauResponse]:
    """Liste les tableaux d'un projet avec le nombre de circuits et la longueur."""
    _check_project_access_read(project_id, db, current_user)
    tableaux = tableau_repository.list_for_project(db, project_id)
    dmap = _derive_map(db, project_id)
    return [_to_response(t, dmap) for t in tableaux]


def _get_tableau_or_404(project_id: str, tableau_id: str, db: Session):
    tab = tableau_repository.get_by_id(db, tableau_id)
    if not tab or tab.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tableau introuvable."
        )
    return tab


@router.get("/{project_id}/tableaux/{tableau_id}/qr.png")
def tableau_qr_png(
    project_id: str,
    tableau_id: str,
    base_url: str = Query("", description="Origine publique (fallback front)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """QR code PNG d'un tableau (encode l'URL publique de sa fiche)."""
    _check_project_access_read(project_id, db, current_user)
    tab = _get_tableau_or_404(project_id, tableau_id, db)
    base = _public_base(base_url)
    png = generate_qr_png(f"{base}/t/{tab.qr_token}")
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{project_id}/tableaux/labels.pdf")
def tableaux_labels_pdf(
    project_id: str,
    base_url: str = Query("", description="Origine publique (fallback front)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Planche A4 d'etiquettes QR (8 par feuille) prete a decouper et coller."""
    project = _check_project_access_read(project_id, db, current_user)
    base = _public_base(base_url)

    tableaux = tableau_repository.list_for_project(db, project_id)
    if not tableaux:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun tableau. Generez-les d'abord depuis un export CANECO.",
        )

    exports = caneco_repository.list_for_project(db, project_id)
    indice = exports[0].indice if exports else "—"

    labels = [
        {
            "repere": t.repere,
            "designation": t.designation or "",
            "url": f"{base}/t/{t.qr_token}",
        }
        for t in tableaux
    ]
    pdf = build_labels_pdf(
        labels,
        project_name=project.name,
        project_code=project.code,
        indice=indice or "—",
    )
    filename = f"etiquettes-tableaux_{project.code}.pdf"
    encoded = urlquote(filename)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded}"
            )
        },
    )


@router.get("/{project_id}/tableaux/{tableau_id}/fiche.pdf")
def tableau_fiche_pdf(
    project_id: str,
    tableau_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Fiche tableau PDF (en-tete rouge VINCI + recapitulatif vertical)."""
    project = _check_project_access_read(project_id, db, current_user)
    tab = _get_tableau_or_404(project_id, tableau_id, db)
    fiche = build_fiche_data(db, tab)
    pdf = build_fiche_pdf(
        repere=fiche.repere,
        designation=fiche.designation,
        project_name=project.name,
        indice=fiche.indice,
        sections=fiche.sections,
    )
    filename = f"fiche-tableau_{tab.repere}_{project.code}.pdf"
    encoded = urlquote(filename)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded}"
            )
        },
    )
