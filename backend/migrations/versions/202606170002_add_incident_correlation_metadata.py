"""add incident correlation metadata

Revision ID: 202606170002
Revises: 202606170001
Create Date: 2026-06-17 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202606170002"
down_revision: Union[str, None] = "202606170001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column(
            "title",
            sa.String(length=255),
            server_default="Untitled incident",
            nullable=False,
        ),
    )
    op.add_column("incidents", sa.Column("suspected_attack_path", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "last_seen")
    op.drop_column("incidents", "first_seen")
    op.drop_column("incidents", "description")
    op.drop_column("incidents", "suspected_attack_path")
    op.drop_column("incidents", "title")
