"""Repository pour VerificationRun et Gap."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.verification import Gap, VerificationRun


# ---------------------------------------------------------------------------
# VerificationRun
# ---------------------------------------------------------------------------


def get_runs_for_project(db: Session, project_id: str) -> list[VerificationRun]:
    """Retourne tous les runs d'un projet, du plus recent au plus ancien."""
    return (
        db.query(VerificationRun)
        .filter(VerificationRun.project_id == project_id)
        .order_by(VerificationRun.created_at.desc())
        .all()
    )


def get_run_by_id(db: Session, run_id: str) -> VerificationRun | None:
    return db.get(VerificationRun, run_id)


def delete_run(db: Session, run: VerificationRun) -> None:
    db.delete(run)
    db.commit()


# ---------------------------------------------------------------------------
# Gap
# ---------------------------------------------------------------------------


def get_gaps_for_run(
    db: Session,
    run_id: str,
    severity: str | None = None,
    status: str | None = None,
    code: str | None = None,
) -> list[Gap]:
    """Retourne les gaps d'un run avec filtres optionnels."""
    q = db.query(Gap).filter(Gap.run_id == run_id)
    if severity:
        q = q.filter(Gap.severity == severity)
    if status:
        q = q.filter(Gap.status == status)
    if code:
        q = q.filter(Gap.code == code)
    return q.order_by(Gap.severity, Gap.code, Gap.created_at).all()


def get_gap_by_id(db: Session, gap_id: str) -> Gap | None:
    return db.get(Gap, gap_id)


def update_gap_status(
    db: Session,
    gap: Gap,
    *,
    status: str,
    comment: str | None,
    resolved_by_id: str | None,
) -> Gap:
    from datetime import datetime, timezone

    gap.status = status
    if comment is not None:
        gap.comment = comment
    if status in ("clos", "justifie", "acquitte"):
        gap.resolved_by_id = resolved_by_id
        gap.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(gap)
    return gap
