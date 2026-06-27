"""add upload ingestion tables

Revision ID: 202606240001
Revises: 202606180001
Create Date: 2026-06-24 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202606240001"
down_revision: Union[str, None] = "202606180001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "uploaded_datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'uploaded'"), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("record_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uploaded_datasets_source_type"), "uploaded_datasets", ["source_type"], unique=False)
    op.create_index(op.f("ix_uploaded_datasets_status"), "uploaded_datasets", ["status"], unique=False)

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["uploaded_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uploaded_files_dataset_id"), "uploaded_files", ["dataset_id"], unique=False)

    op.add_column("raw_events", sa.Column("uploaded_dataset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_raw_events_uploaded_dataset_id"), "raw_events", ["uploaded_dataset_id"], unique=False)
    op.create_foreign_key(
        "fk_raw_events_uploaded_dataset_id_uploaded_datasets",
        "raw_events",
        "uploaded_datasets",
        ["uploaded_dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("normalized_events", sa.Column("uploaded_dataset_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_normalized_events_uploaded_dataset_id"),
        "normalized_events",
        ["uploaded_dataset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_normalized_events_uploaded_dataset_id_uploaded_datasets",
        "normalized_events",
        "uploaded_datasets",
        ["uploaded_dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_normalized_events_uploaded_dataset_id_uploaded_datasets",
        "normalized_events",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_normalized_events_uploaded_dataset_id"), table_name="normalized_events")
    op.drop_column("normalized_events", "uploaded_dataset_id")

    op.drop_constraint(
        "fk_raw_events_uploaded_dataset_id_uploaded_datasets",
        "raw_events",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_raw_events_uploaded_dataset_id"), table_name="raw_events")
    op.drop_column("raw_events", "uploaded_dataset_id")

    op.drop_index(op.f("ix_uploaded_files_dataset_id"), table_name="uploaded_files")
    op.drop_table("uploaded_files")

    op.drop_index(op.f("ix_uploaded_datasets_status"), table_name="uploaded_datasets")
    op.drop_index(op.f("ix_uploaded_datasets_source_type"), table_name="uploaded_datasets")
    op.drop_table("uploaded_datasets")
