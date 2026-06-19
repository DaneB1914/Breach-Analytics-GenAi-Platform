"""add llm summary audit fields

Revision ID: 202606180001
Revises: 202606170002
Create Date: 2026-06-18 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202606180001"
down_revision: Union[str, None] = "202606170002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_summaries",
        sa.Column(
            "attack_timeline",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "llm_summaries",
        sa.Column(
            "affected_users",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "llm_summaries",
        sa.Column(
            "affected_assets",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("llm_summaries", sa.Column("suspected_attack_path", sa.Text(), nullable=True))
    op.add_column(
        "llm_summaries",
        sa.Column(
            "recommended_containment_steps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_summaries", "recommended_containment_steps")
    op.drop_column("llm_summaries", "suspected_attack_path")
    op.drop_column("llm_summaries", "affected_assets")
    op.drop_column("llm_summaries", "affected_users")
    op.drop_column("llm_summaries", "attack_timeline")
