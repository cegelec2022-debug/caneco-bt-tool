"""Add caneco_row and bordereau_row to gaps table.

Revision ID: 009
Revises: 008
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("gaps", sa.Column("caneco_row", sa.Integer(), nullable=True))
    op.add_column("gaps", sa.Column("bordereau_row", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("gaps", "bordereau_row")
    op.drop_column("gaps", "caneco_row")
