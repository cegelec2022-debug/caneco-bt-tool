"""Module B — saisie chantier : table field_entries

Une ligne CANECO (un depart) peut recevoir UNE saisie chantier (longueur reelle
+ commentaire) effectuee par le Chef de Chantier sur le terrain. La saisie
est unique par ligne CANECO ; modifier la saisie revient a la mettre a jour.

Revision ID: 010
Revises: 009
Create Date: 2026-05-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "field_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "caneco_line_id",
            sa.String(length=36),
            sa.ForeignKey("caneco_lines.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("longueur_realisee", sa.Float(), nullable=False),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.Column(
            "saisi_par",
            sa.String(length=36),
            sa.ForeignKey("users.id"),
            nullable=False,
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
    )
    op.create_index(
        "ix_field_entries_caneco_line_id",
        "field_entries",
        ["caneco_line_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_field_entries_caneco_line_id", table_name="field_entries")
    op.drop_table("field_entries")
