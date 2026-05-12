"""Schemas Pydantic pour les imports CPS."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CpsRuleItem(BaseModel):
    """Regle technique extraite du CPS PDF."""

    rule_type: str
    value: str
    unit: str | None = None
    context_label: str | None = None
    description: str
    source_page: int
    source_excerpt: str | None = None
    confidence: float
    requires_validation: bool = True


class CpsImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_name: str
    status: str
    extraction_method: str
    page_count: int | None
    rules_count: int | None
    error_message: str | None
    created_at: datetime
    created_by_id: str | None


class CpsImportDetail(BaseModel):
    """Import CPS avec la liste complete des regles extraites."""

    imp: CpsImportResponse
    rules: list[CpsRuleItem]
