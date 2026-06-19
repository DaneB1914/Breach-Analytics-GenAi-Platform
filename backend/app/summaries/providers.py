from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.summaries.schemas import IncidentEvidence, SummaryDraft


class IncidentSummaryProvider(Protocol):
    """Provider interface so a real LLM implementation can be added later."""

    def generate(self, evidence: IncidentEvidence) -> SummaryDraft:
        ...


class MockIncidentSummaryProvider:
    """Deterministic provider used when no real LLM integration is configured."""

    model_name = "mock-deterministic-v1"

    def generate(self, evidence: IncidentEvidence) -> SummaryDraft:
        users = collect_affected_users(evidence)
        assets = collect_affected_assets(evidence)
        timeline = build_attack_timeline(evidence.events)
        suspected_attack_path = evidence.incident.suspected_attack_path
        alert_names = unique_values(alert.alert_rule_name for alert in evidence.alerts)

        executive_summary = (
            f"Incident {evidence.incident.id} is a {evidence.incident.severity or 'unknown'} "
            f"severity investigation involving {format_list(users) or 'unknown users'} "
            f"and {format_list(assets) or 'unknown assets'}. "
            f"The suspected attack path is: {suspected_attack_path or 'not available'}."
        )
        technical_summary = (
            f"Correlated {len(evidence.alerts)} alerts and {len(evidence.events)} normalized "
            f"events. Alert rules observed: {format_list(alert_names) or 'none'}. "
            f"Evidence event IDs: {format_list([str(event_id) for event_id in evidence.evidence_event_ids])}."
        )

        return SummaryDraft(
            model_name=self.model_name,
            executive_summary=executive_summary,
            technical_summary=technical_summary,
            attack_timeline=timeline,
            affected_users=users,
            affected_assets=assets,
            suspected_attack_path=suspected_attack_path,
            recommended_containment_steps=build_containment_steps(users, assets),
            evidence_event_ids=evidence.evidence_event_ids,
        )


def get_summary_provider(openai_api_key: str | None) -> IncidentSummaryProvider:
    # A real OpenAI-backed provider can replace this branch later. For now, mock
    # mode keeps local development and portfolio demos deterministic and free.
    return MockIncidentSummaryProvider()


def build_attack_timeline(events) -> list[dict]:
    timeline = []

    for event in sorted(
        events,
        key=lambda item: (
            item.event_timestamp or datetime.min.replace(tzinfo=timezone.utc),
            item.id or 0,
        ),
    ):
        timeline.append(
            {
                "event_id": event.id,
                "timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                "source_system": event.source_system,
                "event_type": event.event_type,
                "username": event.username,
                "asset": event.asset,
                "action": event.action,
                "outcome": event.outcome,
                "severity": event.severity,
                "message": event.normalized_message,
            }
        )

    return timeline


def collect_affected_users(evidence: IncidentEvidence) -> list[str]:
    values = [evidence.incident.affected_user]
    values.extend(alert.related_username for alert in evidence.alerts)
    values.extend(event.username for event in evidence.events)
    return unique_values(values)


def collect_affected_assets(evidence: IncidentEvidence) -> list[str]:
    values = list(evidence.incident.affected_assets or [])
    values.extend(alert.related_asset for alert in evidence.alerts)
    values.extend(event.asset for event in evidence.events)
    return unique_values(values)


def build_containment_steps(users: list[str], assets: list[str]) -> list[str]:
    steps = [
        "Preserve incident evidence and keep original normalized event IDs attached to the case.",
        "Review and validate each alert before taking irreversible remediation action.",
    ]

    if users:
        steps.append(f"Disable or reset sessions for affected user accounts: {format_list(users)}.")
    if assets:
        steps.append(f"Isolate or increase monitoring on affected assets: {format_list(assets)}.")

    steps.extend(
        [
            "Revoke suspicious access keys, tokens, and VPN sessions tied to the incident.",
            "Review API export activity and confirm whether data left the environment.",
        ]
    )
    return steps


def unique_values(values) -> list[str]:
    return sorted({str(value) for value in values if value})


def format_list(values: list[str]) -> str:
    return ", ".join(values)
