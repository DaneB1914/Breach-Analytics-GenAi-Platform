from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db.models import LLMSummary
from app.summaries.schemas import IncidentEvidence


def render_markdown_report(
    evidence: IncidentEvidence,
    summary: LLMSummary | None,
    generated_at: datetime | None = None,
) -> str:
    """Render stored incident evidence as a portable Markdown report."""

    incident = evidence.incident
    report_time = generated_at or datetime.now(timezone.utc)
    evidence_ids = summary.evidence_event_ids if summary else evidence.evidence_event_ids
    executive_summary = summary.executive_summary if summary else fallback_executive_summary(evidence)
    technical_summary = summary.technical_summary if summary else fallback_technical_summary(evidence)
    containment_steps = summary.recommended_containment_steps if summary else []

    lines = [
        f"# Incident Investigation Report: {incident.title}",
        "",
        f"**Generated:** {format_timestamp(report_time)}",
        f"**Incident ID:** {incident.id}",
        "",
        "## Incident Overview",
        "",
        incident.description or "No incident description is available.",
        "",
        f"- **Severity:** {display(incident.severity)}",
        f"- **Status:** {display(incident.status)}",
        f"- **Affected user:** {display(incident.affected_user)}",
        f"- **Affected assets:** {', '.join(incident.affected_assets) or 'Not identified'}",
        f"- **First seen:** {format_timestamp(incident.first_seen)}",
        f"- **Last seen:** {format_timestamp(incident.last_seen)}",
        f"- **Suspected attack path:** {display(incident.suspected_attack_path)}",
        "",
        "## Executive Summary",
        "",
        executive_summary,
        "",
        "## Technical Summary",
        "",
        technical_summary,
        "",
        "## Attack Timeline",
        "",
        *render_timeline(evidence, summary),
        "",
        "## Triggered Alerts",
        "",
        *render_alerts(evidence),
        "",
        "## Evidence Event IDs",
        "",
        ", ".join(str(event_id) for event_id in evidence_ids) or "No evidence event IDs are available.",
        "",
        "## Recommended Containment Steps",
        "",
        *render_bullets(containment_steps, "No containment recommendations are available."),
        "",
        "## Analyst Notes",
        "",
        "_Add analyst observations, validation results, decisions, and follow-up actions here._",
        "",
        "## Limitations",
        "",
        "- This report is generated from incident, alert, event, and summary data currently stored in the platform.",
        "- Missing or incomplete source telemetry may affect the investigation narrative.",
        "- AI-assisted content should be validated by a qualified analyst before operational or legal use.",
        "- This Markdown export is intended for investigation support and is not a formal forensic report.",
        "",
    ]

    return "\n".join(lines)


def render_timeline(evidence: IncidentEvidence, summary: LLMSummary | None) -> list[str]:
    if summary and summary.attack_timeline:
        return [
            (
                f"- **{format_timestamp(item.get('timestamp'))}** - "
                f"Event {display(item.get('event_id'))}: "
                f"{display(item.get('source_system'))} / {display(item.get('event_type'))}"
            )
            for item in summary.attack_timeline
        ]

    if evidence.events:
        return [
            (
                f"- **{format_timestamp(event.event_timestamp)}** - Event {event.id}: "
                f"{display(event.source_system)} / {display(event.event_type)} - "
                f"{display(event.normalized_message)}"
            )
            for event in sorted(
                evidence.events,
                key=lambda event: (event.event_timestamp or datetime.min.replace(tzinfo=timezone.utc), event.id or 0),
            )
        ]

    return ["No timeline events are available."]


def render_alerts(evidence: IncidentEvidence) -> list[str]:
    if not evidence.alerts:
        return ["No alerts are linked to this incident."]

    lines = [
        "| Rule | Severity | User | Asset | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for alert in evidence.alerts:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_table(alert.alert_rule_name),
                    escape_table(alert.severity),
                    escape_table(alert.related_username),
                    escape_table(alert.related_asset),
                    escape_table(alert.description),
                ]
            )
            + " |"
        )
    return lines


def render_bullets(items: list[str], empty_message: str) -> list[str]:
    return [f"- {item}" for item in items] if items else [empty_message]


def fallback_executive_summary(evidence: IncidentEvidence) -> str:
    incident = evidence.incident
    return (
        f"Incident {incident.id} is a {display(incident.severity)} severity investigation "
        f"affecting {display(incident.affected_user)}. Generate an LLM summary for a richer narrative."
    )


def fallback_technical_summary(evidence: IncidentEvidence) -> str:
    return (
        f"The incident currently contains {len(evidence.alerts)} linked alerts and "
        f"{len(evidence.events)} normalized evidence events."
    )


def format_timestamp(value: Any) -> str:
    if value in (None, ""):
        return "Not set"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return str(value)


def display(value: Any) -> str:
    if value in (None, ""):
        return "Not set"
    return str(value)


def escape_table(value: Any) -> str:
    return display(value).replace("|", "\\|").replace("\n", " ")
