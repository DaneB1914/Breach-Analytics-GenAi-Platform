"""create breach analytics tables

Revision ID: 202606150001
Revises:
Create Date: 2026-06-15 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202606150001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_events_event_type"), "raw_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_raw_events_source_system"), "raw_events", ["source_system"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'open'"), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("affected_user", sa.String(length=255), nullable=True),
        sa.Column(
            "affected_assets",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incidents_affected_user"), "incidents", ["affected_user"], unique=False)
    op.create_index(op.f("ix_incidents_status"), "incidents", ["status"], unique=False)

    op.create_table(
        "normalized_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_event_id", sa.Integer(), nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("destination_ip", sa.String(length=45), nullable=True),
        sa.Column("asset", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("outcome", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("mitre_technique_id", sa.String(length=50), nullable=True),
        sa.Column("normalized_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["raw_event_id"], ["raw_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_normalized_events_event_type"), "normalized_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_normalized_events_raw_event_id"), "normalized_events", ["raw_event_id"], unique=False)
    op.create_index(op.f("ix_normalized_events_source_ip"), "normalized_events", ["source_ip"], unique=False)
    op.create_index(op.f("ix_normalized_events_source_system"), "normalized_events", ["source_system"], unique=False)
    op.create_index(op.f("ix_normalized_events_username"), "normalized_events", ["username"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_event_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("alert_rule_name", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("mitre_technique_id", sa.String(length=50), nullable=True),
        sa.Column("normalized_message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["normalized_event_id"], ["normalized_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_alert_rule_name"), "alerts", ["alert_rule_name"], unique=False)
    op.create_index(op.f("ix_alerts_incident_id"), "alerts", ["incident_id"], unique=False)
    op.create_index(op.f("ix_alerts_normalized_event_id"), "alerts", ["normalized_event_id"], unique=False)
    op.create_index(op.f("ix_alerts_severity"), "alerts", ["severity"], unique=False)

    op.create_table(
        "incident_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("normalized_event_id", sa.Integer(), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_event_id"], ["normalized_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            "normalized_event_id",
            name="uq_incident_events_incident_normalized_event",
        ),
    )
    op.create_index(op.f("ix_incident_events_incident_id"), "incident_events", ["incident_id"], unique=False)
    op.create_index(
        op.f("ix_incident_events_normalized_event_id"),
        "incident_events",
        ["normalized_event_id"],
        unique=False,
    )

    op.create_table(
        "llm_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("technical_summary", sa.Text(), nullable=False),
        sa.Column(
            "evidence_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_summaries_incident_id"), "llm_summaries", ["incident_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_summaries_incident_id"), table_name="llm_summaries")
    op.drop_table("llm_summaries")

    op.drop_index(op.f("ix_incident_events_normalized_event_id"), table_name="incident_events")
    op.drop_index(op.f("ix_incident_events_incident_id"), table_name="incident_events")
    op.drop_table("incident_events")

    op.drop_index(op.f("ix_alerts_severity"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_normalized_event_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_incident_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_alert_rule_name"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_normalized_events_username"), table_name="normalized_events")
    op.drop_index(op.f("ix_normalized_events_source_system"), table_name="normalized_events")
    op.drop_index(op.f("ix_normalized_events_source_ip"), table_name="normalized_events")
    op.drop_index(op.f("ix_normalized_events_raw_event_id"), table_name="normalized_events")
    op.drop_index(op.f("ix_normalized_events_event_type"), table_name="normalized_events")
    op.drop_table("normalized_events")

    op.drop_index(op.f("ix_incidents_status"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_affected_user"), table_name="incidents")
    op.drop_table("incidents")

    op.drop_index(op.f("ix_raw_events_source_system"), table_name="raw_events")
    op.drop_index(op.f("ix_raw_events_event_type"), table_name="raw_events")
    op.drop_table("raw_events")
