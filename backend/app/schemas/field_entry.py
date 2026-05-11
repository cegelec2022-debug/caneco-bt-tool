"""Schemas Pydantic — saisie chantier (Module B)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Seuil au-dela duquel un commentaire est obligatoire pour justifier l'ecart.
# Une longueur reelle > +50 % ou < -50 % de la longueur prevue (ou nulle alors
# que la prevue est > 0) doit etre justifiee.
ECART_COMMENT_REQUIRED_PCT = 50.0


def commentaire_obligatoire(
    longueur_prevue: float | None, longueur_realisee: float
) -> bool:
    """Indique si une saisie chantier requiert un commentaire de justification.

    Regle metier :
    - reel = 0 alors que prevu > 0 -> commentaire obligatoire (le circuit n'a
      finalement pas ete tire, le BE doit savoir pourquoi) ;
    - ecart absolu > 50 % de la longueur prevue -> commentaire obligatoire.
    """
    if longueur_prevue is None or longueur_prevue <= 0:
        return False
    if longueur_realisee == 0:
        return True
    ecart_pct = abs(longueur_realisee - longueur_prevue) / longueur_prevue * 100.0
    return ecart_pct > ECART_COMMENT_REQUIRED_PCT


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
