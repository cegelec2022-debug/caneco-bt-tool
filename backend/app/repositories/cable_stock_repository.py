"""Acces donnees aux references stock de cables."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.cable_stock import CableStockItem


def get_or_create(
    db: Session,
    *,
    project_id: str,
    type_cable: str,
    section_label: str,
    ame: str,
    section_mm2: float | None,
) -> CableStockItem:
    """Renvoie la reference stock du projet (la cree avec valeurs nulles si absente)."""
    item = (
        db.query(CableStockItem)
        .filter(
            CableStockItem.project_id == project_id,
            CableStockItem.type_cable == type_cable,
            CableStockItem.section_label == section_label,
            CableStockItem.ame == ame,
        )
        .first()
    )
    if item is None:
        item = CableStockItem(
            project_id=project_id,
            type_cable=type_cable,
            section_label=section_label,
            ame=ame,
            section_mm2=section_mm2,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


def update_quantities(
    db: Session,
    item: CableStockItem,
    *,
    quantite_achetee: float | None = None,
    quantite_livree: float | None = None,
    seuil_alerte_min_m: float | None = None,
) -> CableStockItem:
    if quantite_achetee is not None:
        item.quantite_achetee = quantite_achetee
    if quantite_livree is not None:
        item.quantite_livree = quantite_livree
    if seuil_alerte_min_m is not None:
        item.seuil_alerte_min_m = seuil_alerte_min_m
    db.commit()
    db.refresh(item)
    return item


def get_by_id(db: Session, item_id: str) -> CableStockItem | None:
    return db.query(CableStockItem).filter(CableStockItem.id == item_id).first()
