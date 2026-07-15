from datetime import datetime, timezone

from app.db.models import Alert, Incident, LLMSummary, NormalizedEvent
from app.reports.markdown import render_markdown_report
from app.summaries.schemas import IncidentEvidence

NOW = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)


def test_markdown_report_contains_investigation_sections() -> None:
    report = render_markdown_report(
        evidence=sample_evidence(),
        summary=sample_summary(),
        generated_at=datetime(2026, 6, 27, 14, 0, tzinfo=timezone.utc),
    )

    assert "# Incident Investigation Report: High security incident for alex.morgan" in report
    assert "**Generated:** 2026-06-27 14:00:00 UTC" in report
    assert "## Incident Overview" in report
    assert "- **Severity:** high" in report
    assert "- **Status:** open" in report
    assert "- **Affected user:** alex.morgan" in report
    assert "- **Affected assets:** API-GATEWAY-01" in report
    assert "## Executive Summary" in report
    assert "Executive investigation summary" in report
    assert "## Technical Summary" in report
    assert "Technical investigation summary" in report
    assert "## Attack Timeline" in report
    assert "Event 1: api_gateway / bulk_export" in report
    assert "## Triggered Alerts" in report
    assert "Suspicious API data download" in report
    assert "## Evidence Event IDs" in report
    assert "\n1\n" in report
    assert "## Recommended Containment Steps" in report
    assert "Disable the affected account." in report
    assert "## Analyst Notes" in report
    assert "## Limitations" in report


def test_markdown_report_uses_evidence_fallbacks_without_summary() -> None:
    report = render_markdown_report(
        evidence=sample_evidence(),
        summary=None,
        generated_at=NOW,
    )

    assert "Generate an LLM summary for a richer narrative." in report
    assert "1 linked alerts and 1 normalized evidence events" in report
    assert "Large API export" in report
    assert "No containment recommendations are available." in report


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
        severity="high",
        mitre_technique_id="T1530",
        normalized_message="Large API export",
    )

    return IncidentEvidence(
        incident=incident,
        alerts=[alert],
        events=[event],
        evidence_event_ids=[1],
    )


def sample_summary() -> LLMSummary:
    return LLMSummary(
        id=1,
        incident_id=1,
        created_at=NOW,
        model_name="mock-deterministic-v1",
        executive_summary="Executive investigation summary",
        technical_summary="Technical investigation summary",
        attack_timeline=[
            {
                "event_id": 1,
                "timestamp": NOW.isoformat(),
                "source_system": "api_gateway",
                "event_type": "bulk_export",
            }
        ],
        affected_users=["alex.morgan"],
        affected_assets=["API-GATEWAY-01"],
        suspected_attack_path="Suspicious API data download",
        recommended_containment_steps=["Disable the affected account."],
        evidence_event_ids=[1],
    )
