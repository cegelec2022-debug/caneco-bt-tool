"""Schéma initial — 8 tables V1

Revision ID: 001
Revises:
Create Date: 2026-05-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="BE"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client", sa.String(255)),
        sa.Column("agency", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(50), nullable=False, server_default="actif"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
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
    )
    op.create_index("ix_projects_code", "projects", ["code"])

    op.create_table(
        "caneco_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("indice", sa.String(10), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(500)),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("line_count", sa.Integer()),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_caneco_exports_project_id", "caneco_exports", ["project_id"])

    op.create_table(
        "caneco_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "export_id",
            sa.String(36),
            sa.ForeignKey("caneco_exports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("repere", sa.String(100)),
        sa.Column("designation", sa.String(500)),
        sa.Column("style", sa.String(100)),
        sa.Column("nb_recepteurs", sa.Integer()),
        sa.Column("consommation", sa.Float()),
        sa.Column("ib", sa.Float()),
        sa.Column("longueur", sa.Float()),
        sa.Column("type_cable", sa.String(100)),
        sa.Column("cable", sa.String(100)),
        sa.Column("neutre", sa.String(50)),
        sa.Column("pe", sa.String(50)),
        sa.Column("ame", sa.String(10)),
        sa.Column("calibre", sa.Float()),
        sa.Column("bloc_coupure", sa.String(100)),
        sa.Column("bloc_declencheur", sa.String(100)),
        sa.Column("bloc_differentiel", sa.String(100)),
        sa.Column("ir_th_in", sa.Float()),
        sa.Column("ir_mg_in", sa.Float()),
        sa.Column("icu", sa.Float()),
        sa.Column("extra_data", sa.Text()),
    )
    op.create_index("ix_caneco_lines_export_id", "caneco_lines", ["export_id"])

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

    op.create_table(
        "tableaux",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repere", sa.String(100), nullable=False),
        sa.Column("designation", sa.String(500)),
        sa.Column("qr_token", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_tableaux_project_id", "tableaux", ["project_id"])
    op.create_index("ix_tableaux_qr_token", "tableaux", ["qr_token"])

    op.create_table(
        "departures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tableau_id",
            sa.String(36),
            sa.ForeignKey("tableaux.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repere", sa.String(100), nullable=False),
        sa.Column("designation", sa.String(500)),
        sa.Column("style", sa.String(100)),
        sa.Column("longueur_prevue", sa.Float()),
        sa.Column("longueur_realisee", sa.Float()),
        sa.Column("calibre", sa.Float()),
        sa.Column("type_cable", sa.String(100)),
        sa.Column("section", sa.String(100)),
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
    )
    op.create_index("ix_departures_tableau_id", "departures", ["tableau_id"])


def downgrade() -> None:
    op.drop_table("departures")
    op.drop_table("tableaux")
    op.drop_table("bordereau_lines")
    op.drop_table("bordereaux")
    op.drop_table("caneco_lines")
    op.drop_table("caneco_exports")
    op.drop_table("projects")
    op.drop_table("users")
