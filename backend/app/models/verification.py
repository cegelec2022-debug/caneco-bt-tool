import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VerificationRun(Base):
    """Execution du moteur de verification sur un couple CANECO + Bordereau."""

    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    caneco_export_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("caneco_exports.id", ondelete="SET NULL")
    )
    bordereau_import_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bordereau_imports.id", ondelete="SET NULL")
    )
    # pending | running | done | error
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    total_gaps: Mapped[int | None] = mapped_column(Integer)
    critical_count: Mapped[int | None] = mapped_column(Integer)
    warning_count: Mapped[int | None] = mapped_column(Integer)
    signal_count: Mapped[int | None] = mapped_column(Integer)
    info_count: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))


class Gap(Base):
    """Ecart detecte lors d'une verification — un Gap = un constat actionnable."""

    __tablename__ = "gaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # E-001 ... E-010
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # BLOQUANT | A_CORRIGER | A_SIGNALER | INFO
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Repere CANECO implique (ex. "TES1-TD1-1" ou liste de reperes)
    caneco_repere: Mapped[str | None] = mapped_column(String(500))
    # N°Prix bordereau implique
    bordereau_num_prix: Mapped[str | None] = mapped_column(String(100))
    # ouvert | leve | justifie
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ouvert")
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
