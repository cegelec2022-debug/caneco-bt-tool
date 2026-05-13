from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Domaines d'installation NF C 15-100 : conditionne l'applicabilite de certaines regles
# (ex. NFC-012 obligation DDR 30 mA sur prises est specifique a l'habitation).
DomaineInstallation = Literal["habitation", "tertiaire", "industriel", "erp"]


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
    created_by: str | None
    created_at: datetime
    updated_at: datetime
