from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas import EventResponse
from app.db.models import NormalizedEvent

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[EventResponse])
def list_events(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    severity: str | None = None,
    username: str | None = None,
    source_system: str | None = None,
    event_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[NormalizedEvent]:
    statement = select(NormalizedEvent)
    statement = apply_event_filters(
        statement=statement,
        severity=severity,
        username=username,
        source_system=source_system,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
    )
    statement = statement.order_by(
        NormalizedEvent.event_timestamp.desc(),
        NormalizedEvent.id.desc(),
    ).offset(skip).limit(limit)

    return list(db.scalars(statement).all())


@router.get("/events/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)) -> NormalizedEvent:
    event = db.get(NormalizedEvent, event_id)

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return event


def apply_event_filters(
    statement: Select[tuple[NormalizedEvent]],
    severity: str | None,
    username: str | None,
    source_system: str | None,
    event_type: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> Select[tuple[NormalizedEvent]]:
    # Each filter is optional so the endpoint works for broad browsing and focused search.
    if severity:
        statement = statement.where(NormalizedEvent.severity == severity)
    if username:
        statement = statement.where(NormalizedEvent.username == username)
    if source_system:
        statement = statement.where(NormalizedEvent.source_system == source_system)
    if event_type:
        statement = statement.where(NormalizedEvent.event_type == event_type)
    if start_date:
        statement = statement.where(NormalizedEvent.event_timestamp >= start_date)
    if end_date:
        statement = statement.where(NormalizedEvent.event_timestamp <= end_date)

    return statement
