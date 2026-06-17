from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlertCandidate:
    """Alert-like result produced by a detection rule before database insert."""

    rule_name: str
    severity: str
    description: str
    related_username: str | None
    related_asset: str | None
    related_event_ids: list[int]
    primary_event_id: int
    mitre_technique_id: str | None
    first_seen: datetime | None
    last_seen: datetime | None


@dataclass(frozen=True)
class DetectionResult:
    """Summary of one detection run."""

    events_analyzed: int
    alerts_created: int
    alerts_skipped: int
