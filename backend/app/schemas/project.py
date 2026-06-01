from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Domaines d'installation NF C 15-100 : conditionne l'applicabilite de certaines regles
# (ex. NFC-012 obligation DDR 30 mA sur prises est specifique a l'habitation).
DomaineInstallation = Literal["habitation", "tertiaire", "industriel", "erp"]

# Phase du chantier (jalons RA). Sert au filtrage et a l'affichage dashboard.
ProjectPhase = Literal[
    "etudes", "approvisionnement", "pose", "mise_en_service", "reception"
]

# Niveau de priorite (pilote RA). Sert au tri dashboard.
ProjectPriorite = Literal["critique", "standard", "faible"]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    name: str
    client: str | None = None
    agency: str | None = None
    description: str | None = None
    status: str = "actif"
    domaine_installation: DomaineInstallation = "tertiaire"


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    client: str | None = None
    agency: str | None = None
    description: str | None = None
    status: str | None = None
    domaine_installation: DomaineInstallation | None = None
    # Pilotage RA
    phase: ProjectPhase | None = None
    priorite: ProjectPriorite | None = None
    notes_ra: str | None = None
    date_fin_prevue: date | None = None
    # Avancement compose : poids et validation_pct ne sont editables que par
    # le RA / BE proprietaire (controle dans le routeur).
    poids_tirets_pct: float | None = Field(default=None, ge=0, le=100)
    poids_validation_pct: float | None = Field(default=None, ge=0, le=100)
    validation_pct: float | None = Field(default=None, ge=0, le=100)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    client: str | None
    agency: str | None
    description: str | None
    status: str
    domaine_installation: str
    phase: str
    priorite: str
    notes_ra: str | None
    date_fin_prevue: date | None
    poids_tirets_pct: float
    poids_validation_pct: float
    validation_pct: float
    created_by: str | None
    created_at: datetime
    updated_at: datetime
