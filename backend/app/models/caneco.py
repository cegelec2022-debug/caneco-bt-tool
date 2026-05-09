import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CanecoExport(Base):
    """Un export CANECO BT pour un projet donné (un indice = un export)."""

    __tablename__ = "caneco_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indice: Mapped[str] = mapped_column(String(10), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    line_count: Mapped[int | None] = mapped_column(Integer)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CanecoLine(Base):
    """Une ligne de l'export CANECO BT — correspond à un départ ou un tableau."""

    __tablename__ = "caneco_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    export_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("caneco_exports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Colonnes CANECO BT (23 colonnes standard)
    repere: Mapped[str | None] = mapped_column(String(100))
    designation: Mapped[str | None] = mapped_column(String(500))
    style: Mapped[str | None] = mapped_column(String(100))
    nb_recepteurs: Mapped[int | None] = mapped_column(Integer)
    consommation: Mapped[float | None] = mapped_column(Float)
    ib: Mapped[float | None] = mapped_column(Float)
    longueur: Mapped[float | None] = mapped_column(Float)
    type_cable: Mapped[str | None] = mapped_column(String(100))
    cable: Mapped[str | None] = mapped_column(String(100))
    neutre: Mapped[str | None] = mapped_column(String(50))
    pe: Mapped[str | None] = mapped_column(String(50))
    ame: Mapped[str | None] = mapped_column(String(10))
    calibre: Mapped[float | None] = mapped_column(Float)
    bloc_coupure: Mapped[str | None] = mapped_column(String(100))
    bloc_declencheur: Mapped[str | None] = mapped_column(String(100))
    bloc_differentiel: Mapped[str | None] = mapped_column(String(100))
    ir_th_in: Mapped[float | None] = mapped_column(Float)
    ir_mg_in: Mapped[float | None] = mapped_column(Float)
    icu: Mapped[float | None] = mapped_column(Float)

    # Colonnes supplémentaires stockées en JSON texte
    extra_data: Mapped[str | None] = mapped_column(Text)
