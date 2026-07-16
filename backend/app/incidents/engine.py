from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Alert, Incident, IncidentEvent, NormalizedEvent
from app.incidents.correlation import build_incident, group_related_alerts
from app.incidents.schemas import IncidentCorrelationResult, IncidentGroup


def run_incident_correlation(
    session: Session,
    dataset_id: int | None = None,
    sample_only: bool = False,
) -> IncidentCorrelationResult:
    """Create incidents from unassigned alerts in exactly one data scope."""

    statement = select(Alert)
    if dataset_id is not None:
        # Uploaded alerts assigned by the pre-isolation engine may point to a
        # nullable or different-dataset incident. A rerun safely reclaims them.
        statement = statement.outerjoin(Incident, Alert.incident_id == Incident.id).where(
            Alert.dataset_id == dataset_id,
            or_(
                Alert.incident_id.is_(None),
                Incident.dataset_id.is_(None),
                Incident.dataset_id != dataset_id,
            ),
        )
    else:
        statement = statement.where(
            Alert.dataset_id.is_(None),
            Alert.incident_id.is_(None),
        )

    unassigned_alerts = list(
        session.scalars(
            statement.order_by(Alert.first_seen, Alert.id)
        )
    )
    groups = group_related_alerts(unassigned_alerts)

    incidents_created = 0
    alerts_linked = 0
    incident_events_linked = 0

    for group in groups:
        incident = build_incident(group, dataset_id=dataset_id)
        session.add(incident)
        session.flush()
        incidents_created += 1

        alerts_linked += assign_alerts_to_incident(group, incident.id)
        incident_events_linked += add_incident_event_links(
            session,
            group,
            incident.id,
            dataset_id,
        )

    # The app uses autoflush=False. Flush here so any follow-up step in the
    # same transaction, such as summary generation, can see incident links.
    if incidents_created or alerts_linked or incident_events_linked:
        session.flush()

    return IncidentCorrelationResult(
        alerts_analyzed=len(unassigned_alerts),
        incidents_created=incidents_created,
        alerts_linked=alerts_linked,
        incident_events_linked=incident_events_linked,
    )


def assign_alerts_to_incident(group: IncidentGroup, incident_id: int) -> int:
    for alert in group.alerts:
        alert.incident_id = incident_id

    return len(group.alerts)


def add_incident_event_links(
    session: Session,
    group: IncidentGroup,
    incident_id: int,
    dataset_id: int | None = None,
) -> int:
    event_ids = scoped_event_ids(session, group.related_event_ids, dataset_id)

    for event_id in event_ids:
        session.add(
            IncidentEvent(
                incident_id=incident_id,
                normalized_event_id=event_id,
            )
        )

    return len(event_ids)


def scoped_event_ids(
    session: Session,
    event_ids: list[int],
    dataset_id: int | None,
) -> list[int]:
    """Return only evidence IDs owned by the current investigation scope."""

    if not event_ids:
        return []

    statement = select(NormalizedEvent.id).where(NormalizedEvent.id.in_(event_ids))
    if dataset_id is None:
        statement = statement.where(NormalizedEvent.dataset_id.is_(None))
    else:
        statement = statement.where(NormalizedEvent.dataset_id == dataset_id)

    return sorted(session.scalars(statement).all())
