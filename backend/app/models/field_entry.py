"""Module B — saisie chantier (longueur reelle tiree par circuit)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FieldEntry(Base):
    """Saisie chantier pour une ligne CANECO (depart).

    Une seule saisie par ligne CANECO : si le Chef de Chantier remonte plusieurs
    valeurs successives, on met a jour la meme entree.
    """

    __tablename__ = "field_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    caneco_line_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("caneco_lines.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    longueur_realisee: Mapped[float] = mapped_column(Float, nullable=False)
    commentaire: Mapped[str | None] = mapped_column(Text)
    saisi_par: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
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
