from datetime import datetime, timezone

from app.db.models import Alert, Incident, NormalizedEvent
from app.summaries.providers import MockIncidentSummaryProvider
from app.summaries.schemas import IncidentEvidence

NOW = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)


def test_mock_summary_generation() -> None:
    evidence = sample_evidence()

    summary = MockIncidentSummaryProvider().generate(evidence)

    assert summary.model_name == "mock-deterministic-v1"
    assert summary.evidence_event_ids == [1]


def test_summary_includes_executive_summary() -> None:
    summary = MockIncidentSummaryProvider().generate(sample_evidence())

    assert "Incident 1" in summary.executive_summary
    assert "alex.morgan" in summary.executive_summary


def test_summary_includes_technical_summary() -> None:
    summary = MockIncidentSummaryProvider().generate(sample_evidence())

    assert "Correlated 1 alerts and 1 normalized events" in summary.technical_summary
    assert "Suspicious API data download" in summary.technical_summary


def test_summary_includes_event_ids_as_evidence() -> None:
    summary = MockIncidentSummaryProvider().generate(sample_evidence())

    assert summary.evidence_event_ids == [1]
    assert summary.attack_timeline[0]["event_id"] == 1


def sample_evidence() -> IncidentEvidence:
    incident = Incident(
        id=1,
        status="open",
        severity="high",
        title="High security incident for alex.morgan",
        suspected_attack_path="Suspicious API data download",
        description="Correlated API exfiltration alert",
        affected_user="alex.morgan",
        affected_assets=["API-GATEWAY-01"],
        first_seen=NOW,
        last_seen=NOW,
    )
    alert = Alert(
        id=1,
        normalized_event_id=1,
        incident_id=1,
        alert_rule_name="Suspicious API data download",
        severity="high",
        description="Suspicious API download observed",
        related_username="alex.morgan",
        related_asset="API-GATEWAY-01",
        related_event_ids=[1],
        first_seen=NOW,
        last_seen=NOW,
        normalized_message="Suspicious API download observed",
    )
    event = NormalizedEvent(
        id=1,
        raw_event_id=1,
        event_timestamp=NOW,
        source_system="api_gateway",
        event_type="bulk_export",
        username="alex.morgan",
        source_ip="10.8.14.23",
        destination_ip=None,
        asset="API-GATEWAY-01",
        action="GET /api/v1/customers/export?region=all",
        outcome="200",
        severity=None,
        mitre_technique_id=None,
        normalized_message="Large API export",
    )

    return IncidentEvidence(
        incident=incident,
        alerts=[alert],
        events=[event],
        evidence_event_ids=[1],
    )
