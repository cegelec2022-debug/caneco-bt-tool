"""CANECO line v2 — 23 colonnes complètes, métadonnées export

Revision ID: 002
Revises: 001
Create Date: 2026-05-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- caneco_exports : ajout des champs de métadonnées ---
    op.add_column("caneco_exports", sa.Column("lines_read", sa.Integer(), nullable=True))
    op.add_column("caneco_exports", sa.Column("columns_detected", sa.Integer(), nullable=True))
    op.add_column("caneco_exports", sa.Column("columns_mapped", sa.Integer(), nullable=True))
    op.add_column("caneco_exports", sa.Column("extra_columns_count", sa.Integer(), nullable=True))

    # --- caneco_lines : conversion consommation Float → String ---
    op.alter_column(
        "caneco_lines",
        "consommation",
        type_=sa.String(200),
        existing_type=sa.Float(),
        postgresql_using="consommation::text",
        nullable=True,
    )

    # --- caneco_lines : 4 nouvelles colonnes CANECO ---
    op.add_column("caneco_lines", sa.Column("amont", sa.String(200), nullable=True))
    op.add_column("caneco_lines", sa.Column("repere_aval", sa.String(200), nullable=True))
    op.add_column("caneco_lines", sa.Column("nb_cables_multi", sa.Integer(), nullable=True))
    op.add_column("caneco_lines", sa.Column("contacteur", sa.String(100), nullable=True))

    # --- caneco_lines : numéro de ligne Excel et données brutes ---
    op.add_column("caneco_lines", sa.Column("excel_row_number", sa.Integer(), nullable=True))
    op.add_column("caneco_lines", sa.Column("raw_data", sa.Text(), nullable=True))
    op.add_column("caneco_lines", sa.Column("extra_columns", sa.Text(), nullable=True))
    op.create_index("ix_caneco_lines_excel_row_number", "caneco_lines", ["excel_row_number"])


def downgrade() -> None:
    op.drop_index("ix_caneco_lines_excel_row_number", table_name="caneco_lines")
    op.drop_column("caneco_lines", "extra_columns")
    op.drop_column("caneco_lines", "raw_data")
    op.drop_column("caneco_lines", "excel_row_number")
    op.drop_column("caneco_lines", "contacteur")
    op.drop_column("caneco_lines", "nb_cables_multi")
    op.drop_column("caneco_lines", "repere_aval")
    op.drop_column("caneco_lines", "amont")
    op.alter_column(
        "caneco_lines",
        "consommation",
        type_=sa.Float(),
        existing_type=sa.String(200),
        postgresql_using="consommation::double precision",
        nullable=True,
    )
    op.drop_column("caneco_exports", "extra_columns_count")
    op.drop_column("caneco_exports", "columns_mapped")
    op.drop_column("caneco_exports", "columns_detected")
    op.drop_column("caneco_exports", "lines_read")
