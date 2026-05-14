"""Schemas Pydantic pour le carnet de cables."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CableBookEntryResponse(BaseModel):
    """Une ligne du sommaire du carnet."""

    model_config = ConfigDict(from_attributes=True)

    type_cable: str
    cable_caneco: str
    section_mm2: float | None
    nb_conducteurs: int
    nb_circuits_paralleles: int
    longueur_totale_m: float
    nb_occurrences: int
    pourcentage_du_total: float
    reperes_aval: list[str]
    longueurs_par_aval: dict[str, float]


class CableBookReportResponse(BaseModel):
    """Carnet de cables complet : sommaire + rapport synthetique."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[CableBookEntryResponse]
    longueur_totale_projet_m: float
    nb_lignes_caneco_traitees: int
    nb_types_cables_distincts: int
    longueur_par_type_cable: dict[str, float]
    longueur_par_aval: dict[str, float]
    top5: list[CableBookEntryResponse]
