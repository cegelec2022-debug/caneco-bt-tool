"""Module C — Tableau de bord multi-projets pour le RA.

Une vue d'ensemble agregee pour le Responsable d'Affaires : sur tous les
projets accessibles, on remonte les indicateurs cles (avancement chantier,
ecarts ouverts, alertes stock, longueurs prevues vs realisees) afin
d'identifier en un coup d'oeil les projets qui derapent (US-RA-01).

Tous les chiffres sont derives des donnees existantes (CANECO, saisies
chantier, ecarts, stock) — aucune donnee inventee.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.caneco import CanecoExport, CanecoLine
from app.models.field_entry import FieldEntry
from app.models.project import Project
from app.models.user import User, UserRole
from app.models.verification import Gap, VerificationRun
from app.services.cable_stock.service import list_stock
from app.services.project_metrics import compute_project_metrics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    client: str | None
    agency: str | None
    status: str
    indice_caneco: str | None
    nb_tableaux: int
    nb_circuits: int
    nb_circuits_saisis: int
    avancement_pct: float
    pct_tirets: float
    validation_pct: float
    longueur_prevue_m: float
    longueur_realisee_m: float
    nb_ecarts_ouverts: int
    nb_ecarts_bloquants: int
    nb_alertes_stock: int
    derniere_activite: datetime | None
    # Pilotage RA
    phase: str
    priorite: str
    date_fin_prevue: date | None


class DashboardSummary(BaseModel):
    """Vue globale : totaux + liste projets enrichis."""

    nb_projets: int
    nb_projets_actifs: int
    nb_ecarts_ouverts_total: int
    nb_ecarts_bloquants_total: int
    nb_alertes_stock_total: int
    avancement_moyen_pct: float
    longueur_prevue_totale_m: float
    longueur_realisee_totale_m: float
    projets: list[ProjectSummary]


def _check_dashboard_access(user: User) -> None:
    """Seuls ADMIN / RA accedent au tableau de bord (US-RA-01)."""
    if user.role not in (UserRole.ADMIN, UserRole.RA):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tableau de bord reserve au Responsable d'Affaires.",
        )


def _latest_export(db: Session, project_id: str) -> CanecoExport | None:
    return (
        db.query(CanecoExport)
        .filter(CanecoExport.project_id == project_id)
        .order_by(CanecoExport.uploaded_at.desc())
        .first()
    )


def _build_project_summary(db: Session, project: Project) -> ProjectSummary:
    """Agrege les indicateurs cles d'un projet pour le tableau de bord RA."""
    export = _latest_export(db, project.id)

    # Charge les lignes CANECO du dernier export + les saisies chantier
    lines: list[CanecoLine] = []
    if export:
        lines = db.query(CanecoLine).filter(CanecoLine.export_id == export.id).all()
    line_ids = [cl.id for cl in lines]
    entries: list[FieldEntry] = []
    if line_ids:
        entries = (
            db.query(FieldEntry)
            .filter(FieldEntry.caneco_line_id.in_(line_ids))
            .all()
        )

    # Indicateurs de chantier : SOURCE UNIQUE partagee avec tous les autres
    # ecrans (Tableaux, Saisie chantier...) pour garantir la coherence.
    # On passe ``project`` pour que l'avancement integre la ponderation RA
    # et le % de validation manuel.
    metrics = compute_project_metrics(lines, entries, project)
    nb_tableaux = metrics.nb_tableaux
    nb_circuits = metrics.nb_circuits
    nb_saisis = metrics.nb_circuits_saisis
    avancement = metrics.avancement_pct
    long_prevue = metrics.longueur_prevue_m
    long_realisee = metrics.longueur_realisee_m

    # Ecarts ouverts (status != 'leve') sur la derniere verification du projet
    last_run = (
        db.query(VerificationRun)
        .filter(VerificationRun.project_id == project.id)
        .order_by(VerificationRun.created_at.desc())
        .first()
    )
    nb_ecarts_ouverts = 0
    nb_ecarts_bloquants = 0
    if last_run is not None:
        gaps_q = db.query(Gap).filter(
            Gap.run_id == last_run.id, Gap.status != "leve"
        )
        nb_ecarts_ouverts = gaps_q.count()
        # La severite peut etre stockee en majuscules (ex. "BLOQUANT") selon
        # l'historique des migrations : on accepte les deux formes.
        nb_ecarts_bloquants = gaps_q.filter(
            func.upper(Gap.severity) == "BLOQUANT"
        ).count()

    # Alertes stock : on reutilise le service stock pour avoir le bon decompte
    stock_items = list_stock(db, project.id, lines, entries)
    nb_alertes_stock = sum(1 for s in stock_items if s.en_alerte)

    # Derniere activite : derniere saisie ou derniere verification
    derniere_activite: datetime | None = None
    if entries:
        last_entry = max(entries, key=lambda e: e.updated_at)
        derniere_activite = last_entry.updated_at
    if last_run and (
        derniere_activite is None or last_run.created_at > derniere_activite
    ):
        derniere_activite = last_run.created_at

    return ProjectSummary(
        id=project.id,
        code=project.code,
        name=project.name,
        client=project.client,
        agency=project.agency,
        status=project.status,
        indice_caneco=export.indice if export else None,
        nb_tableaux=nb_tableaux,
        nb_circuits=nb_circuits,
        nb_circuits_saisis=nb_saisis,
        avancement_pct=round(avancement, 1),
        pct_tirets=round(metrics.pct_tirets, 1),
        validation_pct=round(metrics.validation_pct, 1),
        longueur_prevue_m=round(long_prevue, 2),
        longueur_realisee_m=round(long_realisee, 2),
        nb_ecarts_ouverts=nb_ecarts_ouverts,
        nb_ecarts_bloquants=nb_ecarts_bloquants,
        nb_alertes_stock=nb_alertes_stock,
        derniere_activite=derniere_activite,
        phase=project.phase,
        priorite=project.priorite,
        date_fin_prevue=project.date_fin_prevue,
    )


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    """Vue globale RA : tous les projets enrichis + totaux."""
    _check_dashboard_access(current_user)

    projects = (
        db.query(Project).order_by(Project.created_at.desc()).all()
    )
    summaries = [_build_project_summary(db, p) for p in projects]

    nb_actifs = sum(1 for p in projects if p.status == "actif")
    avancement_moyen = (
        sum(s.avancement_pct for s in summaries) / len(summaries)
        if summaries
        else 0.0
    )
    return DashboardSummary(
        nb_projets=len(summaries),
        nb_projets_actifs=nb_actifs,
        nb_ecarts_ouverts_total=sum(s.nb_ecarts_ouverts for s in summaries),
        nb_ecarts_bloquants_total=sum(s.nb_ecarts_bloquants for s in summaries),
        nb_alertes_stock_total=sum(s.nb_alertes_stock for s in summaries),
        avancement_moyen_pct=round(avancement_moyen, 1),
        longueur_prevue_totale_m=round(
            sum(s.longueur_prevue_m for s in summaries), 2
        ),
        longueur_realisee_totale_m=round(
            sum(s.longueur_realisee_m for s in summaries), 2
        ),
        projets=summaries,
    )
