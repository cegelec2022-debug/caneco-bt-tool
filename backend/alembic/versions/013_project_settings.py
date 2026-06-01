"""Parametres projet : avancement compose + phase + priorite + notes RA + date fin.

L'avancement projet est desormais une combinaison ponderee entre :
- le % de cable tire sur chantier (calcule a partir des field_entries),
- le % de validation manuelle saisi par le RA.

Le RA configure les poids (par defaut 70 / 30) et le % validation. Les autres
champs (phase, priorite, notes, date_fin_prevue) servent au pilotage du
portefeuille de projets dans le tableau de bord RA.

Revision ID: 013
Revises: 012
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "poids_tirets_pct",
                sa.Float(),
                nullable=False,
                server_default="70",
            )
        )
        batch_op.add_column(
            sa.Column(
                "poids_validation_pct",
                sa.Float(),
                nullable=False,
                server_default="30",
            )
        )
        batch_op.add_column(
            sa.Column(
                "validation_pct",
                sa.Float(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "phase",
                sa.String(length=30),
                nullable=False,
                server_default="etudes",
            )
        )
        batch_op.add_column(
            sa.Column(
                "priorite",
                sa.String(length=20),
                nullable=False,
                server_default="standard",
            )
        )
        batch_op.add_column(sa.Column("notes_ra", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("date_fin_prevue", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("date_fin_prevue")
        batch_op.drop_column("notes_ra")
        batch_op.drop_column("priorite")
        batch_op.drop_column("phase")
        batch_op.drop_column("validation_pct")
        batch_op.drop_column("poids_validation_pct")
        batch_op.drop_column("poids_tirets_pct")
