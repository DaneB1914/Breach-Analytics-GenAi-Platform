from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import configure_mappers

from app.db import models  # noqa: F401  Import models so they register with Base.metadata.
from app.db.base import Base


def test_sqlalchemy_mappers_configure_successfully() -> None:
    configure_mappers()


def test_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "raw_events",
        "normalized_events",
        "alerts",
        "incidents",
        "incident_events",
        "llm_summaries",
    }


def test_breach_analytics_columns_are_available() -> None:
    expected_columns = {
        "raw_events": {
            "id",
            "ingested_at",
            "event_timestamp",
            "source_system",
            "event_type",
            "raw_payload",
        },
        "normalized_events": {
            "id",
            "raw_event_id",
            "normalized_at",
            "event_timestamp",
            "source_system",
            "event_type",
            "username",
            "source_ip",
            "destination_ip",
            "asset",
            "action",
            "outcome",
            "severity",
            "mitre_technique_id",
            "normalized_message",
        },
        "alerts": {
            "id",
            "normalized_event_id",
            "incident_id",
            "created_at",
            "alert_rule_name",
            "severity",
            "description",
            "related_username",
            "related_asset",
            "related_event_ids",
            "mitre_technique_id",
            "first_seen",
            "last_seen",
            "normalized_message",
        },
        "incidents": {
            "id",
            "created_at",
            "updated_at",
            "status",
            "severity",
            "title",
            "suspected_attack_path",
            "description",
            "affected_user",
            "affected_assets",
            "first_seen",
            "last_seen",
        },
        "incident_events": {
            "id",
            "incident_id",
            "normalized_event_id",
            "linked_at",
        },
        "llm_summaries": {
            "id",
            "incident_id",
            "created_at",
            "model_name",
            "executive_summary",
            "technical_summary",
            "evidence_event_ids",
        },
    }

    for table_name, column_names in expected_columns.items():
        assert set(Base.metadata.tables[table_name].columns.keys()) == column_names


def test_jsonb_columns_store_flexible_payloads_and_evidence() -> None:
    assert isinstance(Base.metadata.tables["raw_events"].c.raw_payload.type, JSONB)
    assert isinstance(Base.metadata.tables["incidents"].c.affected_assets.type, JSONB)
    assert isinstance(Base.metadata.tables["alerts"].c.related_event_ids.type, JSONB)
    assert isinstance(Base.metadata.tables["llm_summaries"].c.evidence_event_ids.type, JSONB)
