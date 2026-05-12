"""Verification runs and gaps tables.

Revision ID: 006
Revises: 005
Create Date: 2026-05-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "caneco_export_id",
            sa.String(36),
            sa.ForeignKey("caneco_exports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "bordereau_import_id",
            sa.String(36),
            sa.ForeignKey("bordereau_imports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cps_import_id",
            sa.String(36),
            sa.ForeignKey("cps_imports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("config_snapshot", JSON(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_gaps", sa.Integer(), nullable=True),
        sa.Column("critical_count", sa.Integer(), nullable=True),
        sa.Column("high_count", sa.Integer(), nullable=True),
        sa.Column("medium_count", sa.Integer(), nullable=True),
        sa.Column("info_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_table(
        "gaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("verification_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(20), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("fields_compared", JSON(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("norm_rule_code", sa.String(20), nullable=True),
        sa.Column(
            "caneco_line_id",
            sa.String(36),
            sa.ForeignKey("caneco_lines.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "bordereau_line_id",
            sa.String(36),
            sa.ForeignKey("bordereau_lines.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("caneco_repere", sa.String(500), nullable=True),
        sa.Column("bordereau_num_prix", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ouvert"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "resolved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("gaps")
    op.drop_table("verification_runs")
