import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Valeurs autorisees pour project.phase et project.priorite.
# Centralisees ici pour pouvoir les exposer aux schemas et au frontend.
PROJECT_PHASES: tuple[str, ...] = (
    "etudes",
    "approvisionnement",
    "pose",
    "mise_en_service",
    "reception",
)
PROJECT_PRIORITES: tuple[str, ...] = ("critique", "standard", "faible")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client: Mapped[str | None] = mapped_column(String(255))
    agency: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="actif")
    domaine_installation: Mapped[str] = mapped_column(
        String(50), nullable=False, default="tertiaire"
    )

    # --- Avancement compose (RA configurable) -------------------------------
    # avancement = poids_tirets/100 * pct_tirets + poids_validation/100 * validation_pct
    # Defaut : 70 % cable tire, 30 % validation. Le RA peut ajuster les poids
    # et saisit validation_pct manuellement (jalon valide / a valider).
    poids_tirets_pct: Mapped[float] = mapped_column(Float, nullable=False, default=70.0)
    poids_validation_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=30.0
    )
    validation_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # --- Pilotage RA --------------------------------------------------------
    phase: Mapped[str] = mapped_column(String(30), nullable=False, default="etudes")
    priorite: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    notes_ra: Mapped[str | None] = mapped_column(Text)
    date_fin_prevue: Mapped[date | None] = mapped_column(Date)

    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
