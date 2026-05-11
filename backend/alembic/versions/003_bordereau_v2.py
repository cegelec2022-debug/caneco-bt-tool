"""Bordereau v2 — Remplacement du schema simple par les tables hierarchiques

Revision ID: 003
Revises: 002
Create Date: 2026-05-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supprimer les anciennes tables dans l'ordre des FK
    op.drop_index("ix_bordereau_lines_bordereau_id", table_name="bordereau_lines")
    op.drop_table("bordereau_lines")
    op.drop_index("ix_bordereaux_project_id", table_name="bordereaux")
    op.drop_table("bordereaux")

    # bordereau_imports
    op.create_table(
        "bordereau_imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(500)),
        sa.Column("indice", sa.String(20)),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),
        sa.Column("total_lines", sa.Integer()),
        sa.Column("total_articles", sa.Integer()),
        sa.Column("sections_count", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_bordereau_imports_project_id", "bordereau_imports", ["project_id"])

    # bordereau_sections
    op.create_table(
        "bordereau_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "bordereau_import_id",
            sa.String(36),
            sa.ForeignKey("bordereau_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("excel_row_number", sa.Integer()),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_bordereau_sections_import_id", "bordereau_sections", ["bordereau_import_id"]
    )

    # bordereau_lines (nouveau schema)
    op.create_table(
        "bordereau_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "bordereau_import_id",
            sa.String(36),
            sa.ForeignKey("bordereau_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            sa.String(36),
            sa.ForeignKey("bordereau_sections.id", ondelete="SET NULL"),
        ),
        sa.Column("excel_row_number", sa.Integer()),
        sa.Column("num_prix", sa.String(50)),
        sa.Column("designation", sa.String(500)),
        sa.Column("unite", sa.String(20)),
        sa.Column("quantite", sa.Float()),
        sa.Column("quantite_raw", sa.String(100)),
        sa.Column("sous_famille", sa.String(500)),
        sa.Column("detected_section_mm2", sa.String(50)),
        sa.Column("detected_material", sa.String(20)),
        sa.Column("detected_cable_type", sa.String(50)),
        sa.Column("detected_kind", sa.String(50)),
    )
    op.create_index("ix_bordereau_lines_import_id", "bordereau_lines", ["bordereau_import_id"])


def downgrade() -> None:
    op.drop_index("ix_bordereau_lines_import_id", table_name="bordereau_lines")
    op.drop_table("bordereau_lines")
    op.drop_index("ix_bordereau_sections_import_id", table_name="bordereau_sections")
    op.drop_table("bordereau_sections")
    op.drop_index("ix_bordereau_imports_project_id", table_name="bordereau_imports")
    op.drop_table("bordereau_imports")

    # Recreer les anciennes tables
    op.create_table(
        "bordereaux",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(500)),
        sa.Column("sheet_name", sa.String(255)),
        sa.Column("line_count", sa.Integer()),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_bordereaux_project_id", "bordereaux", ["project_id"])

    op.create_table(
        "bordereau_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "bordereau_id",
            sa.String(36),
            sa.ForeignKey("bordereaux.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("n_prix", sa.String(100)),
        sa.Column("designation", sa.String(500)),
        sa.Column("unite", sa.String(50)),
        sa.Column("quantite", sa.Float()),
        sa.Column("prix_unitaire", sa.Float()),
        sa.Column("montant", sa.Float()),
    )
    op.create_index("ix_bordereau_lines_bordereau_id", "bordereau_lines", ["bordereau_id"])
