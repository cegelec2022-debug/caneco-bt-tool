"""Schemas Pydantic — saisie chantier (Module B)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FieldEntryUpsert(BaseModel):
    """Payload pour creer / mettre a jour la saisie d'une ligne CANECO."""

    model_config = ConfigDict(extra="forbid")  # interdit id, saisi_par injecte par body

    longueur_realisee: float = Field(ge=0, le=100_000, description="Longueur en metres")
    commentaire: str | None = Field(None, max_length=2000)


class FieldEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    caneco_line_id: str
    longueur_realisee: float
    commentaire: str | None
    saisi_par: str
    created_at: datetime
    updated_at: datetime
