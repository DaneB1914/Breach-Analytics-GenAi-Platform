from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, NormalizedEvent
from app.detections.rules import collect_alert_candidates
from app.detections.schemas import AlertCandidate, DetectionResult


def run_detections(
    session: Session,
    dataset_id: int | None = None,
    sample_only: bool = False,
) -> DetectionResult:
    """Apply rules to one uploaded dataset or to nullable demo events."""

    statement = select(NormalizedEvent)
    if dataset_id is not None:
        statement = statement.where(NormalizedEvent.dataset_id == dataset_id)
    else:
        # A missing dataset ID always means the built-in demo scope. This keeps
        # CLI and API runs from accidentally analyzing every analyst upload.
        statement = statement.where(NormalizedEvent.dataset_id.is_(None))

    events = list(
        session.scalars(
            statement.order_by(
                NormalizedEvent.event_timestamp,
                NormalizedEvent.id,
            )
        )
    )
    candidates = collect_alert_candidates(events)

    alerts_created = 0
    alerts_skipped = 0

    for candidate in candidates:
        if alert_already_exists(session, candidate, dataset_id):
            alerts_skipped += 1
            continue

        session.add(build_alert(candidate, dataset_id))
        alerts_created += 1

    # The app uses autoflush=False. Flush here so a follow-up workflow step in
    # the same transaction, such as incident correlation, can see new alerts.
    if alerts_created:
        session.flush()

    return DetectionResult(
        events_analyzed=len(events),
        alerts_created=alerts_created,
        alerts_skipped=alerts_skipped,
    )


def alert_already_exists(
    session: Session,
    candidate: AlertCandidate,
    dataset_id: int | None,
) -> bool:
    statement = select(Alert).where(Alert.alert_rule_name == candidate.rule_name)
    if dataset_id is None:
        statement = statement.where(Alert.dataset_id.is_(None))
    else:
        statement = statement.where(Alert.dataset_id == dataset_id)

    existing_alerts = session.scalars(statement).all()
    candidate_event_ids = sorted(candidate.related_event_ids)

    return any(
        sorted(alert.related_event_ids or []) == candidate_event_ids
        for alert in existing_alerts
    )


def build_alert(candidate: AlertCandidate, dataset_id: int | None = None) -> Alert:
    return Alert(
        dataset_id=dataset_id,
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
