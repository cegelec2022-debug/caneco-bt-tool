"""Add domaine_installation to projects.

Revision ID: 007
Revises: 006
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "domaine_installation",
            sa.String(50),
            nullable=False,
            server_default="tertiaire",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "domaine_installation")
