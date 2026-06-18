from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, IncidentEvent
from app.incidents.correlation import build_incident, group_related_alerts
from app.incidents.schemas import IncidentCorrelationResult, IncidentGroup


def run_incident_correlation(session: Session) -> IncidentCorrelationResult:
    """Create incidents from alerts that have not been assigned yet."""

    unassigned_alerts = list(
        session.scalars(
            select(Alert)
            .where(Alert.incident_id.is_(None))
            .order_by(Alert.first_seen, Alert.id)
        )
    )
    groups = group_related_alerts(unassigned_alerts)

    incidents_created = 0
    alerts_linked = 0
    incident_events_linked = 0

    for group in groups:
        incident = build_incident(group)
        session.add(incident)
        session.flush()
        incidents_created += 1

        alerts_linked += assign_alerts_to_incident(group, incident.id)
        incident_events_linked += add_incident_event_links(session, group, incident.id)

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
) -> int:
    for event_id in group.related_event_ids:
        session.add(
            IncidentEvent(
                incident_id=incident_id,
                normalized_event_id=event_id,
            )
        )

    return len(group.related_event_ids)
