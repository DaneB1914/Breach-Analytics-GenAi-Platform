from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.db.models import Alert


@dataclass(frozen=True)
class IncidentGroup:
    """Alerts and derived fields that should become one Incident."""

    alerts: list[Alert]
    title: str
    severity: str
    affected_user: str | None
    affected_assets: list[str]
    related_event_ids: list[int]
    suspected_attack_path: str
    description: str
    first_seen: datetime | None
    last_seen: datetime | None


@dataclass(frozen=True)
class IncidentCorrelationResult:
    """Summary of one incident correlation run."""

    alerts_analyzed: int
    incidents_created: int
    alerts_linked: int
    incident_events_linked: int
