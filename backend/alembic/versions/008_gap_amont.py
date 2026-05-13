"""Add caneco_amont to gaps table.

Revision ID: 008
Revises: 007
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gaps",
        sa.Column("caneco_amont", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gaps", "caneco_amont")
