"""Module B+ : ajout date d'achat et date prevue de livraison sur cable_stock_items.

Ces champs sont saisis par le RA pour anticiper les livraisons et permettre au
chef de chantier de planifier les tirages. Ils sont en lecture seule pour le
chef (cf. routeur cable_stock).

Revision ID: 012
Revises: 011
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cable_stock_items") as batch_op:
        batch_op.add_column(sa.Column("date_achat", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("date_livraison_prevue", sa.Date(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("cable_stock_items") as batch_op:
        batch_op.drop_column("date_livraison_prevue")
        batch_op.drop_column("date_achat")
