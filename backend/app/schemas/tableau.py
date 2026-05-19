"""Schemas Pydantic pour les tableaux electriques et la fiche publique.

La reponse publique (FichePublicResponse) est volontairement minimale : elle
n'expose ni le code projet, ni le client, ni les autres tableaux — uniquement
ce qui est necessaire a l'affichage de la fiche scannee (garde-fou securite).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TableauResponse(BaseModel):
    """Un tableau (vue authentifiee — BE / RA / admin)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repere: str
    designation: str | None
    qr_token: str
    nb_departs: int
    longueur_totale_m: float


class TableauxGenerateResponse(BaseModel):
    """Resultat de la (re)generation des tableaux d'un projet."""

    model_config = ConfigDict(from_attributes=True)

    caneco_indice: str
    nb_tableaux: int
    nb_departs_total: int
    tableaux: list[TableauResponse]


class FicheRow(BaseModel):
    """Une ligne (libelle / valeur) d'une section de fiche."""

    label: str
    value: str | None


class FicheSection(BaseModel):
    """Un theme de la fiche (Identification, Puissance, Cable, Protection)."""

    title: str
    rows: list[FicheRow]


class FichePublicResponse(BaseModel):
    """Donnees minimales de la fiche tableau accessible par scan QR.

    Lecture seule. Aucune information client ni projet complet.
    """

    model_config = ConfigDict(from_attributes=True)

    repere: str
    designation: str | None
    project_name: str
    indice: str
    nb_departs: int
    sections: list[FicheSection]
