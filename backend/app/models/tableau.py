import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tableau(Base):
    """Tableau électrique d'un projet — chaque tableau a un QR code unique."""

    __tablename__ = "tableaux"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repere: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(500))
    # Token aléatoire long — payload du QR code (sans info projet ni tableau)
    qr_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Departure(Base):
    """Un départ issu d'un tableau — unité de tirage de câble."""

    __tablename__ = "departures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tableau_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tableaux.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repere: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(500))
    style: Mapped[str | None] = mapped_column(String(100))
    longueur_prevue: Mapped[float | None] = mapped_column(Float)
    longueur_realisee: Mapped[float | None] = mapped_column(Float)
    calibre: Mapped[float | None] = mapped_column(Float)
    type_cable: Mapped[str | None] = mapped_column(String(100))
    section: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
