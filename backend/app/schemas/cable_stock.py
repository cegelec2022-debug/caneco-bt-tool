"""Schemas Pydantic — suivi de stock cables."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CableStockItemUpsert(BaseModel):
    """Payload pour identifier une reference et fournir des quantites.

    Le RA ou le Chef de Chantier peut ajuster ces valeurs. Une reference est
    identifiee par (type_cable, section_label, ame).
    """

    model_config = ConfigDict(extra="forbid")

    type_cable: str = Field(min_length=1, max_length=100)
    section_label: str = Field(min_length=1, max_length=50)
    ame: str = Field("", max_length=20)
    section_mm2: float | None = Field(default=None, ge=0)
    quantite_achetee: float | None = Field(default=None, ge=0, le=10_000_000)
    quantite_livree: float | None = Field(default=None, ge=0, le=10_000_000)
    seuil_alerte_min_m: float | None = Field(default=None, ge=0, le=1_000_000)


class CableStockItemResponse(BaseModel):
    """Une reference stock + quantite utilisee calculee a la volee."""

    model_config = ConfigDict(from_attributes=True)

    item_id: str | None
    type_cable: str
    section_label: str
    ame: str
    section_mm2: float | None
    quantite_achetee: float
    quantite_livree: float
    quantite_utilisee: float
    stock_restant: float
    seuil_alerte_min_m: float
    en_alerte: bool


class CableStockReport(BaseModel):
    """Vue complete du stock pour un projet."""

    model_config = ConfigDict(from_attributes=True)

    items: list[CableStockItemResponse]
    nb_references: int
    nb_alertes: int
    quantite_achetee_totale: float
    quantite_livree_totale: float
    quantite_utilisee_totale: float
