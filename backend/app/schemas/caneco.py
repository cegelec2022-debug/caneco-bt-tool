import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CanecoExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    indice: str
    file_name: str
    status: str
    line_count: int | None
    lines_read: int | None
    columns_detected: int | None
    columns_mapped: int | None
    extra_columns_count: int | None
    uploaded_by: str | None
    uploaded_at: datetime


class CanecoLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    export_id: str
    excel_row_number: int | None
    row_index: int

    # 23 colonnes CANECO BT standard
    amont: str | None
    repere_aval: str | None
    repere: str | None
    designation: str | None
    style: str | None
    nb_recepteurs: int | None
    consommation: str | None
    ib: float | None
    longueur: float | None
    type_cable: str | None
    nb_cables_multi: int | None
    cable: str | None
    neutre: str | None
    pe: str | None
    calibre: float | None
    bloc_coupure: str | None
    bloc_declencheur: str | None
    bloc_differentiel: str | None
    ir_th_in: float | None
    ir_mg_in: float | None
    icu: float | None
    contacteur: str | None
    ame: str | None

    # Valeurs brutes : dict {nom_champ: valeur_brute_excel}
    raw_data: dict[str, str] | None = None
    # Colonnes supplémentaires non standard : dict {nom_entete_excel: valeur}
    extra_columns: dict[str, Any] | None = None

    @field_validator("raw_data", "extra_columns", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v


class CanecoExportDetail(BaseModel):
    """Export avec ses lignes paginées."""

    export: CanecoExportResponse
    lines: list[CanecoLineResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
