"""Route publique de la fiche tableau (scan QR) — SEULE route non authentifiee.

Garde-fous (CLAUDE.md) :
- Token long aleatoire (genere par secrets.token_urlsafe(32) sur le modele).
- Lecture seule, aucune modification possible.
- Reponse minimale : repere, designation, nom de projet, recapitulatif. Ni
  code projet, ni client, ni liste des autres tableaux.
- 404 generique (pas de fuite d'information sur l'existence d'un token).
- Rate limiting pour empecher l'enumeration / le scraping de tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.ratelimit import limiter
from app.repositories import project_repository, tableau_repository
from app.schemas.tableau import FichePublicResponse
from app.services.qr.pdf import build_fiche_pdf
from app.services.tableau.fiche import build_fiche_data

router = APIRouter(prefix="/api/t", tags=["public"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Fiche introuvable."
)


def _resolve(token: str, db: Session):
    """Resout token -> (tableau, projet) ou 404 generique."""
    tableau = tableau_repository.get_by_token(db, token)
    if not tableau:
        raise _NOT_FOUND
    project = project_repository.get_by_id(db, tableau.project_id)
    if not project:
        raise _NOT_FOUND
    return tableau, project


@router.get("/{token}", response_model=FichePublicResponse)
@limiter.limit("60/minute")
def fiche_publique(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> FichePublicResponse:
    """Fiche tableau (donnees minimales) accessible par scan QR, sans login."""
    tableau, project = _resolve(token, db)
    fiche = build_fiche_data(db, tableau)
    return FichePublicResponse(
        repere=fiche.repere,
        designation=fiche.designation,
        project_name=project.name,
        indice=fiche.indice,
        nb_departs=fiche.nb_departs,
        sections=fiche.sections,
    )


@router.get("/{token}/fiche.pdf")
@limiter.limit("30/minute")
def fiche_publique_pdf(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> Response:
    """Telechargement PDF de la fiche tableau (lecture seule, sans login)."""
    tableau, project = _resolve(token, db)
    fiche = build_fiche_data(db, tableau)
    pdf = build_fiche_pdf(
        repere=fiche.repere,
        designation=fiche.designation,
        project_name=project.name,
        indice=fiche.indice,
        sections=fiche.sections,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="fiche-tableau_{fiche.repere}.pdf"'
        },
    )
