"""add alert detection metadata

Revision ID: 202606170001
Revises: 202606150001
Create Date: 2026-06-17 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202606170001"
down_revision: Union[str, None] = "202606150001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column("description", sa.Text(), server_default="", nullable=False),
    )
    op.add_column("alerts", sa.Column("related_username", sa.String(length=255), nullable=True))
    op.add_column("alerts", sa.Column("related_asset", sa.String(length=255), nullable=True))
    op.add_column(
        "alerts",
        sa.Column(
            "related_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("alerts", sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_alerts_related_username"), "alerts", ["related_username"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_related_username"), table_name="alerts")
    op.drop_column("alerts", "last_seen")
    op.drop_column("alerts", "first_seen")
    op.drop_column("alerts", "related_event_ids")
    op.drop_column("alerts", "related_asset")
    op.drop_column("alerts", "related_username")
    op.drop_column("alerts", "description")
