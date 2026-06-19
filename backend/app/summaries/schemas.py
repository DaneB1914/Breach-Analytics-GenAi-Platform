from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.db.models import Alert, Incident, NormalizedEvent


@dataclass(frozen=True)
class IncidentEvidence:
    """Evidence bundle sent to a summary provider."""

    incident: Incident
    alerts: list[Alert]
    events: list[NormalizedEvent]
    evidence_event_ids: list[int]


@dataclass(frozen=True)
class SummaryDraft:
    """Summary content before it is stored in LLMSummary."""

    model_name: str
    executive_summary: str
    technical_summary: str
    attack_timeline: list[dict]
    affected_users: list[str]
    affected_assets: list[str]
    suspected_attack_path: str | None
    recommended_containment_steps: list[str]
    evidence_event_ids: list[int]
