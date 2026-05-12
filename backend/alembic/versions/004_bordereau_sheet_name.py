"""Bordereau import — ajout colonne sheet_name

Revision ID: 004
Revises: 003
Create Date: 2026-05-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bordereau_imports", sa.Column("sheet_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("bordereau_imports", "sheet_name")
