"""Stock de cables par reference projet x (type, section, ame).

La quantite utilisee n'est PAS stockee dans ce modele : elle est calculee a
la volee depuis les saisies chantier (field_entries) pour rester en phase
avec les longueurs reellement tirees.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CableStockItem(Base):
    __tablename__ = "cable_stock_items"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "type_cable",
            "section_label",
            "ame",
            name="uq_cable_stock_ref",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Reference identifiant le cable (memes cles que le carnet de cables)
    type_cable: Mapped[str] = mapped_column(String(100), nullable=False)
    section_label: Mapped[str] = mapped_column(String(50), nullable=False)
    ame: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    section_mm2: Mapped[float | None] = mapped_column(Float)

    # Quantites en metres lineaires
    quantite_achetee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantite_livree: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Seuil d'alerte : si stock restant < seuil_alerte_min_m, on alerte le Chef.
    seuil_alerte_min_m: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
