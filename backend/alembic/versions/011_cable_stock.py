"""Module B+ : suivi du stock de cables par reference.

Stocke pour chaque reference (projet x type_cable x section_label x ame) :
- la quantite achetee par le RA,
- la quantite livree / recue par le Chef de Chantier,
- le seuil d'alerte (en metres de stock restant minimum) configurable.

La quantite utilisee n'est PAS stockee : elle est calculee a la volee a partir
des saisies chantier (field_entries) groupees comme dans le carnet de cables,
pour rester auto-synchronisee a chaque mise a jour.

Revision ID: 011
Revises: 010
Create Date: 2026-05-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cable_stock_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type_cable", sa.String(length=100), nullable=False),
        sa.Column("section_label", sa.String(length=50), nullable=False),
        sa.Column("ame", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("section_mm2", sa.Float(), nullable=True),
        sa.Column(
            "quantite_achetee",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "quantite_livree",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "seuil_alerte_min_m",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "type_cable",
            "section_label",
            "ame",
            name="uq_cable_stock_ref",
        ),
    )


def downgrade() -> None:
    op.drop_table("cable_stock_items")
