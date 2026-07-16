"""add dataset field mappings

Revision ID: 202607150002
Revises: 202607150001
Create Date: 2026-07-15 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202607150002"
down_revision: Union[str, None] = "202607150001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_field_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("source_field", sa.String(length=255), nullable=False),
        sa.Column("target_field", sa.String(length=50), nullable=False),
        sa.Column(
            "transformation_type",
            sa.String(length=50),
            server_default=sa.text("'direct'"),
            nullable=False,
        ),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["uploaded_datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "source_field",
            name="uq_dataset_field_mappings_dataset_source",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "target_field",
            name="uq_dataset_field_mappings_dataset_target",
        ),
    )
    op.create_index(
        op.f("ix_dataset_field_mappings_dataset_id"),
        "dataset_field_mappings",
        ["dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_dataset_field_mappings_dataset_id"),
        table_name="dataset_field_mappings",
    )
    op.drop_table("dataset_field_mappings")
