import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Bordereau(Base):
    """Un bordereau de prix uploadé pour un projet."""

    __tablename__ = "bordereaux"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    sheet_name: Mapped[str | None] = mapped_column(String(255))
    line_count: Mapped[int | None] = mapped_column(Integer)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BordereauLine(Base):
    """Une ligne du bordereau de prix (feuille BDP_ELECTRICITE CFO)."""

    __tablename__ = "bordereau_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bordereau_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bordereaux.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)

    n_prix: Mapped[str | None] = mapped_column(String(100))
    designation: Mapped[str | None] = mapped_column(String(500))
    unite: Mapped[str | None] = mapped_column(String(50))
    quantite: Mapped[float | None] = mapped_column(Float)
    prix_unitaire: Mapped[float | None] = mapped_column(Float)
    montant: Mapped[float | None] = mapped_column(Float)
