"""Schemas Pydantic pour le carnet de cables."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CableBookEntryResponse(BaseModel):
    """Une ligne du sommaire du carnet (methode CANECO : par section + ame)."""

    model_config = ConfigDict(from_attributes=True)

    type_cable: str
    cable_caneco: str          # ex. "3G2,5" ou "1*240 mm²"
    section_mm2: float | None
    nb_conducteurs: int
    nb_circuits_paralleles: int
    longueur_totale_m: float
    nb_occurrences: int
    pourcentage_du_total: float
    reperes_aval: list[str]
    longueurs_par_aval: dict[str, float]
    ame: str = ""              # "Cuivre" / "Alu" / ""


# --- Carnet par tableau (vue PDF CANECO) ----------------------------------


class DepartRowResponse(BaseModel):
    """Une ligne de depart dans le carnet d'un tableau (style PDF CANECO)."""

    model_config = ConfigDict(from_attributes=True)

    caneco_line_id: str
    amont: str
    repere: str
    longueur: float | None
    type_cable: str | None
    ame: str
    nb_cables_multi: int | None
    cable: str | None
    neutre: str | None
    pe_pen: str | None
    # Saisie chantier (Module B)
    longueur_realisee: float | None = None
    commentaire_chantier: str | None = None
    saisi_par: str | None = None


class CarnetTableauResponse(BaseModel):
    """Carnet de cables d'un tableau (en-tete + departs)."""

    model_config = ConfigDict(from_attributes=True)

    repere: str
    designation: str | None
    nb_departs: int
    longueur_totale_m: float
    departs: list[DepartRowResponse]


class CarnetParTableauResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tableaux: list[CarnetTableauResponse]
    nb_tableaux: int
    nb_departs_total: int
    longueur_totale_m: float


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
