from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.api.schemas import (
    AlertResponse,
    EventResponse,
    IncidentDetailResponse,
    IncidentResponse,
    LLMSummaryResponse,
)
from app.db.models import Incident, IncidentEvent
from app.summaries.service import generate_and_store_summary, get_latest_summary

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentResponse])
def list_incidents(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    severity: str | None = None,
    status: str | None = None,
    affected_user: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Incident]:
    statement = select(Incident)
    statement = apply_incident_filters(
        statement=statement,
        severity=severity,
        status=status,
        affected_user=affected_user,
        start_date=start_date,
        end_date=end_date,
    )
    statement = statement.order_by(Incident.first_seen.desc(), Incident.id.desc()).offset(skip).limit(limit)

    return list(db.scalars(statement).all())


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> IncidentDetailResponse:
    incident = db.get(
        Incident,
        incident_id,
        options=[
            selectinload(Incident.alerts),
            selectinload(Incident.event_links).selectinload(IncidentEvent.normalized_event),
        ],
    )

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return build_incident_detail_response(incident)


@router.post("/incidents/{incident_id}/summarize", response_model=LLMSummaryResponse)
def summarize_incident(incident_id: int, db: Session = Depends(get_db)) -> LLMSummaryResponse:
    # Summary generation is one transaction: gather evidence, generate, and store.
    with db.begin():
        summary = generate_and_store_summary(db, incident_id)

    if summary is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return LLMSummaryResponse.model_validate(summary)


@router.get("/incidents/{incident_id}/summary", response_model=LLMSummaryResponse)
def get_incident_summary(incident_id: int, db: Session = Depends(get_db)) -> LLMSummaryResponse:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    summary = get_latest_summary(db, incident_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")

    return LLMSummaryResponse.model_validate(summary)


def apply_incident_filters(
    statement: Select[tuple[Incident]],
    severity: str | None,
    status: str | None,
    affected_user: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> Select[tuple[Incident]]:
    if severity:
        statement = statement.where(Incident.severity == severity)
    if status:
        statement = statement.where(Incident.status == status)
    if affected_user:
        statement = statement.where(Incident.affected_user == affected_user)
    if start_date:
        statement = statement.where(Incident.first_seen >= start_date)
    if end_date:
        statement = statement.where(Incident.last_seen <= end_date)

    return statement


def build_incident_detail_response(incident: Incident) -> IncidentDetailResponse:
    related_events = [
        event_link.normalized_event
        for event_link in incident.event_links
        if event_link.normalized_event is not None
    ]

    return IncidentDetailResponse(
        id=incident.id,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        status=incident.status,
        severity=incident.severity,
        title=incident.title,
        suspected_attack_path=incident.suspected_attack_path,
        description=incident.description,
        affected_user=incident.affected_user,
        affected_assets=incident.affected_assets,
        first_seen=incident.first_seen,
        last_seen=incident.last_seen,
        alerts=[AlertResponse.model_validate(alert) for alert in incident.alerts],
        related_events=[EventResponse.model_validate(event) for event in related_events],
    )
