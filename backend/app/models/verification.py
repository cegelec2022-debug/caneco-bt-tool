import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VerificationRun(Base):
    """Execution du moteur de verification croisee CANECO + Bordereau + CPS."""

    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    caneco_export_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("caneco_exports.id", ondelete="SET NULL")
    )
    bordereau_import_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bordereau_imports.id", ondelete="SET NULL")
    )
    cps_import_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cps_imports.id", ondelete="SET NULL")
    )

    # pending | running | done | error
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # manual | auto
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    # Snapshot de la configuration au moment du run (options de verification, versions)
    config_snapshot: Mapped[dict | None] = mapped_column(JSON)
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Compteurs d'ecarts par severite
    total_gaps: Mapped[int | None] = mapped_column(Integer)
    critical_count: Mapped[int | None] = mapped_column(Integer)   # BLOQUANT
    high_count: Mapped[int | None] = mapped_column(Integer)       # A_CORRIGER
    medium_count: Mapped[int | None] = mapped_column(Integer)     # A_SIGNALER
    info_count: Mapped[int | None] = mapped_column(Integer)       # INFO

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))


class Gap(Base):
    """Ecart detecte lors d'une verification — un Gap = un constat actionnable."""

    __tablename__ = "gaps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("verification_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Code ecart : E-001 … E-020
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Titre court pour l'affichage
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # BLOQUANT | A_CORRIGER | A_SIGNALER | INFO
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    # Description detaillee de l'ecart
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Champs compares (JSON : {"field": "section_mm2", "caneco": 2.5, "bordereau": 4.0})
    fields_compared: Mapped[dict | None] = mapped_column(JSON)
    # Action correctrice suggeree
    suggested_action: Mapped[str | None] = mapped_column(Text)

    # Code de la regle normative ou heuristique a l'origine du gap (NFC-001, SUG-001, etc.)
    norm_rule_code: Mapped[str | None] = mapped_column(String(20))

    # Liens vers les entites source
    caneco_line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("caneco_lines.id", ondelete="SET NULL"), index=True
    )
    bordereau_line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bordereau_lines.id", ondelete="SET NULL"), index=True
    )

    # Reperes lisibles (denormalises pour affichage rapide sans jointure)
    caneco_repere: Mapped[str | None] = mapped_column(String(500))
    bordereau_num_prix: Mapped[str | None] = mapped_column(String(100))

    # ouvert | acquitte | justifie | clos
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ouvert")
    comment: Mapped[str | None] = mapped_column(Text)

    resolved_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
