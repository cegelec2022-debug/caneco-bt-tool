"""Endpoints suivi de stock cables (Module B+)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.access import ensure_project_access_read
from app.api.deps import get_current_user, get_db
from app.models.caneco import CanecoLine
from app.models.field_entry import FieldEntry
from app.models.user import User, UserRole
from app.repositories import cable_stock_repository, caneco_repository
from app.schemas.cable_stock import (
    CableStockItemResponse,
    CableStockItemUpsert,
    CableStockReport,
)
from app.services.cable_stock.service import list_stock

router = APIRouter(prefix="/api/projects", tags=["cable-stock"])

# Champs reserves au RA / BE / ADMIN : le chef de chantier ne saisit que la
# quantite livree (et son seuil d'alerte personnel). Les achats et dates
# d'appro sont du ressort du RA.
_RA_ONLY_FIELDS: tuple[str, ...] = (
    "quantite_achetee",
    "date_achat",
    "date_livraison_prevue",
)


def _build_response(items) -> CableStockReport:
    achetee = sum(it.quantite_achetee for it in items)
    livree = sum(it.quantite_livree for it in items)
    utilisee = sum(it.quantite_utilisee for it in items)
    nb_alertes = sum(1 for it in items if it.en_alerte)
    return CableStockReport(
        items=[
            CableStockItemResponse(
                item_id=it.item_id,
                type_cable=it.type_cable,
                section_label=it.section_label,
                ame=it.ame,
                section_mm2=it.section_mm2,
                quantite_achetee=round(it.quantite_achetee, 2),
                quantite_livree=round(it.quantite_livree, 2),
                quantite_utilisee=round(it.quantite_utilisee, 2),
                stock_restant=it.stock_restant,
                seuil_alerte_min_m=it.seuil_alerte_min_m,
                en_alerte=it.en_alerte,
                date_achat=it.date_achat,
                date_livraison_prevue=it.date_livraison_prevue,
            )
            for it in items
        ],
        nb_references=len(items),
        nb_alertes=nb_alertes,
        quantite_achetee_totale=round(achetee, 2),
        quantite_livree_totale=round(livree, 2),
        quantite_utilisee_totale=round(utilisee, 2),
    )


def _load_lines_and_entries(
    db: Session, project_id: str
) -> tuple[list[CanecoLine], list[FieldEntry]]:
    """Charge les lignes CANECO du dernier export et les saisies chantier du projet."""
    exports = caneco_repository.list_for_project(db, project_id)
    lines: list[CanecoLine] = []
    if exports:
        lines = (
            db.query(CanecoLine)
            .filter(CanecoLine.export_id == exports[0].id)
            .all()
        )

    line_ids = [cl.id for cl in lines]
    entries: list[FieldEntry] = []
    if line_ids:
        entries = (
            db.query(FieldEntry)
            .filter(FieldEntry.caneco_line_id.in_(line_ids))
            .all()
        )
    return lines, entries


@router.get(
    "/{project_id}/cable-stock",
    response_model=CableStockReport,
)
def get_cable_stock(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CableStockReport:
    """Vue complete du stock : references + utilisation calculee + alertes."""
    ensure_project_access_read(db, project_id, current_user)
    lines, entries = _load_lines_and_entries(db, project_id)
    items = list_stock(db, project_id, lines, entries)
    return _build_response(items)


@router.put(
    "/{project_id}/cable-stock",
    response_model=CableStockReport,
)
def upsert_cable_stock(
    project_id: str,
    payload: CableStockItemUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CableStockReport:
    """Cree ou met a jour une reference stock (achete / livre / seuil).

    Identification par (type_cable, section_label, ame). Les champs nuls ne
    modifient pas la valeur existante (utile pour mettre a jour partiellement).
    """
    ensure_project_access_read(db, project_id, current_user)

    # Verrouillage des champs reserves au RA pour le chef de chantier.
    # On ignore les valeurs nulles non envoyees (pas de tentative reelle).
    if current_user.role == UserRole.CHEF_CHANTIER:
        sent = payload.model_fields_set
        forbidden_sent = [f for f in _RA_ONLY_FIELDS if f in sent]
        if forbidden_sent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Le chef de chantier ne peut pas modifier "
                    + ", ".join(forbidden_sent)
                    + ". Ces champs sont reserves au RA."
                ),
            )

    item = cable_stock_repository.get_or_create(
        db,
        project_id=project_id,
        type_cable=payload.type_cable.strip(),
        section_label=payload.section_label.strip(),
        ame=payload.ame.strip(),
        section_mm2=payload.section_mm2,
    )

    # Sentinelle : on ne touche aux dates que si le RA les a explicitement
    # envoyees dans le payload (None autorise pour effacer).
    sent_fields = payload.model_fields_set
    update_kwargs: dict = {
        "quantite_achetee": payload.quantite_achetee,
        "quantite_livree": payload.quantite_livree,
        "seuil_alerte_min_m": payload.seuil_alerte_min_m,
    }
    if "date_achat" in sent_fields:
        update_kwargs["date_achat"] = payload.date_achat
    if "date_livraison_prevue" in sent_fields:
        update_kwargs["date_livraison_prevue"] = payload.date_livraison_prevue

    cable_stock_repository.update_quantities(db, item, **update_kwargs)

    lines, entries = _load_lines_and_entries(db, project_id)
    items = list_stock(db, project_id, lines, entries)
    return _build_response(items)


@router.delete(
    "/{project_id}/cable-stock/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_cable_stock_item(
    project_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime une reference stock (les saisies chantier ne sont pas touchees)."""
    ensure_project_access_read(db, project_id, current_user)
    if current_user.role == UserRole.CHEF_CHANTIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le chef de chantier ne peut pas supprimer de reference stock.",
        )
    item = cable_stock_repository.get_by_id(db, item_id)
    if item is None or item.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reference introuvable."
        )
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
