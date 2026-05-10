from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CanecoExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    indice: str
    file_name: str
    status: str
    line_count: int | None
    uploaded_by: str | None
    uploaded_at: datetime


class CanecoLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    export_id: str
    row_index: int
    repere: str | None
    designation: str | None
    style: str | None
    nb_recepteurs: int | None
    consommation: float | None
    ib: float | None
    longueur: float | None
    type_cable: str | None
    cable: str | None
    neutre: str | None
    pe: str | None
    ame: str | None
    calibre: float | None
    bloc_coupure: str | None
    bloc_declencheur: str | None
    bloc_differentiel: str | None
    ir_th_in: float | None
    ir_mg_in: float | None
    icu: float | None
    extra_data: str | None


class CanecoExportDetail(BaseModel):
    """Export avec ses lignes paginées."""

    export: CanecoExportResponse
    lines: list[CanecoLineResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
