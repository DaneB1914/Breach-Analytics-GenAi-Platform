from __future__ import annotations

from app.summaries.schemas import IncidentEvidence


def build_auditable_prompt(evidence: IncidentEvidence) -> str:
    """Build a future LLM prompt that forbids unsupported claims."""

    alert_lines = [
        f"- Alert {alert.id}: {alert.alert_rule_name}; severity={alert.severity}; "
        f"user={alert.related_username}; asset={alert.related_asset}; events={alert.related_event_ids}"
        for alert in evidence.alerts
    ]
    event_lines = [
        f"- Event {event.id}: {event.event_timestamp}; {event.source_system}; "
        f"{event.event_type}; user={event.username}; asset={event.asset}; action={event.action}; "
        f"outcome={event.outcome}; message={event.normalized_message}"
        for event in evidence.events
    ]

    return "\n".join(
        [
            "You are summarizing a breach investigation.",
            "Use only the incident, alert, and event evidence below.",
            "Do not invent users, assets, timelines, impacts, or containment actions.",
            f"Incident: {evidence.incident.id} - {evidence.incident.title}",
            f"Suspected attack path: {evidence.incident.suspected_attack_path}",
            "Alerts:",
            *alert_lines,
            "Events:",
            *event_lines,
        ]
    )
