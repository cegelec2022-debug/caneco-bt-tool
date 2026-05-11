"""Schemas Pydantic pour les bordereaux de prix."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BordereauImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_name: str
    indice: str | None
    status: str
    total_lines: int | None
    total_articles: int | None
    sections_count: int | None
    error_message: str | None
    created_at: datetime
    created_by_id: str | None


class BordereauSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bordereau_import_id: str
    code: str
    title: str | None
    excel_row_number: int | None
    order_index: int


class BordereauLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bordereau_import_id: str
    section_id: str | None
    excel_row_number: int | None
    num_prix: str | None
    designation: str | None
    unite: str | None
    quantite: float | None
    quantite_raw: str | None
    sous_famille: str | None
    detected_section_mm2: str | None
    detected_material: str | None
    detected_cable_type: str | None
    detected_kind: str | None


class BordereauDetail(BaseModel):
    """Import avec ses lignes paginées et ses sections disponibles."""

    imp: BordereauImportResponse
    sections: list[BordereauSectionResponse]
    lines: list[BordereauLineResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
