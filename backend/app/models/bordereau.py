import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BordereauImport(Base):
    """Import d'un fichier bordereau de prix pour un projet."""

    __tablename__ = "bordereau_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    indice: Mapped[str | None] = mapped_column(String(20))
    # Nom de la feuille Excel utilisee lors du parsing
    sheet_name: Mapped[str | None] = mapped_column(String(255))
    # uploaded | parsing | parsed | error
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    total_lines: Mapped[int | None] = mapped_column(Integer)
    total_articles: Mapped[int | None] = mapped_column(Integer)
    sections_count: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))


class BordereauSection(Base):
    """Section principale du bordereau (501 Poste livraison, 505 Cables, 507 Tableaux, etc.)."""

    __tablename__ = "bordereau_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bordereau_import_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bordereau_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    excel_row_number: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class BordereauLine(Base):
    """Article du bordereau (ex. 505.3 — 1x240mm2 Aluminium, ML, 5250)."""

    __tablename__ = "bordereau_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bordereau_import_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bordereau_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bordereau_sections.id", ondelete="SET NULL")
    )
    excel_row_number: Mapped[int | None] = mapped_column(Integer)
    num_prix: Mapped[str | None] = mapped_column(String(50))
    designation: Mapped[str | None] = mapped_column(String(500))
    unite: Mapped[str | None] = mapped_column(String(20))
    quantite: Mapped[float | None] = mapped_column(Float)
    quantite_raw: Mapped[str | None] = mapped_column(String(100))
    sous_famille: Mapped[str | None] = mapped_column(String(500))

    # Champs enrichis par le parser (detection regex depuis la designation)
    detected_section_mm2: Mapped[str | None] = mapped_column(String(50))
    detected_material: Mapped[str | None] = mapped_column(String(20))
    detected_cable_type: Mapped[str | None] = mapped_column(String(50))
    # cable | tableau | chemin_cable | tubage | appareillage | paratonnerre | parafoudre | autre
    detected_kind: Mapped[str | None] = mapped_column(String(50))
