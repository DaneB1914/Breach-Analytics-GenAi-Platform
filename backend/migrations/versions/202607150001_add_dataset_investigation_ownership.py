"""add dataset ownership to alerts and incidents

Revision ID: 202607150001
Revises: 202606240001
Create Date: 2026-07-15 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202607150001"
down_revision: Union[str, None] = "202606240001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("dataset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_alerts_dataset_id"), "alerts", ["dataset_id"], unique=False)
    op.create_foreign_key(
        "fk_alerts_dataset_id_uploaded_datasets",
        "alerts",
        "uploaded_datasets",
        ["dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("incidents", sa.Column("dataset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_incidents_dataset_id"), "incidents", ["dataset_id"], unique=False)
    op.create_foreign_key(
        "fk_incidents_dataset_id_uploaded_datasets",
        "incidents",
        "uploaded_datasets",
        ["dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Existing uploaded alerts inherit ownership from their primary event.
    op.execute(
        """
        UPDATE alerts AS alert
        SET dataset_id = event.uploaded_dataset_id
        FROM normalized_events AS event
        WHERE alert.normalized_event_id = event.id
          AND event.uploaded_dataset_id IS NOT NULL
        """
    )

    # Backfill an incident only when every linked alert belongs to one dataset.
    # Ambiguous legacy incidents remain NULL and continue to behave as demo data.
    op.execute(
        """
        UPDATE incidents AS incident
        SET dataset_id = ownership.dataset_id
        FROM (
            SELECT
                incident_id,
                MIN(dataset_id) AS dataset_id
            FROM alerts
            WHERE incident_id IS NOT NULL
            GROUP BY incident_id
            HAVING COUNT(*) = COUNT(dataset_id)
               AND COUNT(DISTINCT dataset_id) = 1
        ) AS ownership
        WHERE incident.id = ownership.incident_id
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_incidents_dataset_id_uploaded_datasets",
        "incidents",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_incidents_dataset_id"), table_name="incidents")
    op.drop_column("incidents", "dataset_id")

    op.drop_constraint(
        "fk_alerts_dataset_id_uploaded_datasets",
        "alerts",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_alerts_dataset_id"), table_name="alerts")
    op.drop_column("alerts", "dataset_id")
