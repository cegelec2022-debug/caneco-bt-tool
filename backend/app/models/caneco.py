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
    # Nombre de lignes brutes lues dans le fichier (avant dédoublonnage)
    lines_read: Mapped[int | None] = mapped_column(Integer)
    # Colonnes détectées dans l'en-tête
    columns_detected: Mapped[int | None] = mapped_column(Integer)
    columns_mapped: Mapped[int | None] = mapped_column(Integer)
    extra_columns_count: Mapped[int | None] = mapped_column(Integer)
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
    # Numéro de ligne dans la feuille Excel (2 = première donnée, car ligne 1 = en-tête)
    excel_row_number: Mapped[int | None] = mapped_column(Integer, index=True)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # 23 colonnes CANECO BT (dans l'ordre de la feuille)
    amont: Mapped[str | None] = mapped_column(String(200))           # col 0 — Amont
    repere_aval: Mapped[str | None] = mapped_column(String(200))     # col 1 — Repère aval
    repere: Mapped[str | None] = mapped_column(String(100))          # col 2 — Repère
    designation: Mapped[str | None] = mapped_column(String(500))     # col 3 — Désignation
    style: Mapped[str | None] = mapped_column(String(100))           # col 4 — Style
    nb_recepteurs: Mapped[int | None] = mapped_column(Integer)       # col 5 — Nb récepteurs
    consommation: Mapped[str | None] = mapped_column(String(200))    # col 6 — Consommation (ex. "800kVA")
    ib: Mapped[float | None] = mapped_column(Float)                  # col 7 — IB
    longueur: Mapped[float | None] = mapped_column(Float)            # col 8 — Longueur
    type_cable: Mapped[str | None] = mapped_column(String(100))      # col 9 — Type de câble
    nb_cables_multi: Mapped[int | None] = mapped_column(Integer)     # col 10 — Nb câbles multi
    cable: Mapped[str | None] = mapped_column(String(100))           # col 11 — Câble
    neutre: Mapped[str | None] = mapped_column(String(50))           # col 12 — Neutre
    pe: Mapped[str | None] = mapped_column(String(50))               # col 13 — PE ou PEN
    calibre: Mapped[float | None] = mapped_column(Float)             # col 14 — Calibre
    bloc_coupure: Mapped[str | None] = mapped_column(String(100))    # col 15 — Bloc de coupure
    bloc_declencheur: Mapped[str | None] = mapped_column(String(100))# col 16 — Bloc déclencheur
    bloc_differentiel: Mapped[str | None] = mapped_column(String(100))# col 17 — Bloc différentiel
    ir_th_in: Mapped[float | None] = mapped_column(Float)            # col 18 — IrTh / IN
    ir_mg_in: Mapped[float | None] = mapped_column(Float)            # col 19 — IrMg / IN
    icu: Mapped[float | None] = mapped_column(Float)                 # col 20 — Icu
    contacteur: Mapped[str | None] = mapped_column(String(100))      # col 21 — Contacteur
    ame: Mapped[str | None] = mapped_column(String(10))              # col 22 — Ame

    # Valeurs brutes telles qu'elles apparaissent dans Excel (JSON : {col_name: raw_str})
    raw_data: Mapped[str | None] = mapped_column(Text)

    # Colonnes supplémentaires non reconnues par le schéma standard (JSON)
    extra_columns: Mapped[str | None] = mapped_column(Text)
