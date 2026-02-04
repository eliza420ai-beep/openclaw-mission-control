"""add agent token hash

Revision ID: d3e4f5a6b7c8
Revises: c7f0a2b1d4e3
Create Date: 2026-02-04 06:50:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "c7f0a2b1d4e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("agent_token_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(
        op.f("ix_agents_agent_token_hash"),
        "agents",
        ["agent_token_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agents_agent_token_hash"), table_name="agents")
    op.drop_column("agents", "agent_token_hash")
