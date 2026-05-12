"""Modele SQLAlchemy pour les imports CPS (Cahier des Prescriptions Speciales)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CpsImport(Base):
    """Import d'un CPS PDF — extraction des exigences techniques chiffrables."""

    __tablename__ = "cps_imports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    # uploaded | parsing | parsed | error
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    # regex_v1 | llm_v2_pending
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False, default="regex_v1")
    page_count: Mapped[int | None] = mapped_column(Integer)
    rules_count: Mapped[int | None] = mapped_column(Integer)
    # Liste de dicts : {rule_type, value, unit, context_label, description,
    #                   source_page, source_excerpt, confidence, requires_validation}
    extracted_rules: Mapped[list | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
