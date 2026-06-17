from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, NormalizedEvent
from app.detections.rules import collect_alert_candidates
from app.detections.schemas import AlertCandidate, DetectionResult


def run_detections(session: Session) -> DetectionResult:
    """Load normalized events, apply rules, and insert new alerts."""

    events = list(
        session.scalars(
            select(NormalizedEvent).order_by(
                NormalizedEvent.event_timestamp,
                NormalizedEvent.id,
            )
        )
    )
    candidates = collect_alert_candidates(events)

    alerts_created = 0
    alerts_skipped = 0

    for candidate in candidates:
        if alert_already_exists(session, candidate):
            alerts_skipped += 1
            continue

        session.add(build_alert(candidate))
        alerts_created += 1

    return DetectionResult(
        events_analyzed=len(events),
        alerts_created=alerts_created,
        alerts_skipped=alerts_skipped,
    )


def alert_already_exists(session: Session, candidate: AlertCandidate) -> bool:
    existing_alerts = session.scalars(
        select(Alert).where(Alert.alert_rule_name == candidate.rule_name)
    ).all()
    candidate_event_ids = sorted(candidate.related_event_ids)

    return any(
        sorted(alert.related_event_ids or []) == candidate_event_ids
        for alert in existing_alerts
    )


def build_alert(candidate: AlertCandidate) -> Alert:
    return Alert(
        normalized_event_id=candidate.primary_event_id,
        alert_rule_name=candidate.rule_name,
        severity=candidate.severity,
        description=candidate.description,
        related_username=candidate.related_username,
        related_asset=candidate.related_asset,
        related_event_ids=candidate.related_event_ids,
        mitre_technique_id=candidate.mitre_technique_id,
        first_seen=candidate.first_seen,
        last_seen=candidate.last_seen,
        normalized_message=candidate.description,
    )
