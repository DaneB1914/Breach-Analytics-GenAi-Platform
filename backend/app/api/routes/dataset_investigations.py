from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.api.routes.incidents import build_incident_detail_response
from app.api.schemas import (
    AlertResponse,
    EventResponse,
    IncidentDetailResponse,
    IncidentResponse,
    LLMSummaryResponse,
)
from app.db.models import Alert, Incident, IncidentEvent, NormalizedEvent, UploadedDataset
from app.reports.service import generate_incident_markdown_report
from app.summaries.service import generate_and_store_summary, get_latest_summary

router = APIRouter(
    prefix="/uploads/{dataset_id}",
    tags=["dataset investigations"],
)


@router.get("/events", response_model=list[EventResponse])
def list_dataset_events(
    dataset_id: int,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> list[NormalizedEvent]:
    get_dataset_or_404(db, dataset_id)
    statement = (
        select(NormalizedEvent)
        .where(NormalizedEvent.dataset_id == dataset_id)
        .order_by(NormalizedEvent.event_timestamp.desc(), NormalizedEvent.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/alerts", response_model=list[AlertResponse])
def list_dataset_alerts(
    dataset_id: int,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> list[Alert]:
    get_dataset_or_404(db, dataset_id)
    statement = (
        select(Alert)
        .where(Alert.dataset_id == dataset_id)
        .order_by(Alert.first_seen.desc(), Alert.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/incidents", response_model=list[IncidentResponse])
def list_dataset_incidents(
    dataset_id: int,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> list[Incident]:
    get_dataset_or_404(db, dataset_id)
    statement = (
        select(Incident)
        .where(Incident.dataset_id == dataset_id)
        .order_by(Incident.first_seen.desc(), Incident.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_dataset_incident(
    dataset_id: int,
    incident_id: int,
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    get_dataset_or_404(db, dataset_id)
    incident = load_dataset_incident(db, dataset_id, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found in this dataset")
    return build_incident_detail_response(incident)


@router.post("/incidents/{incident_id}/summarize", response_model=LLMSummaryResponse)
def summarize_dataset_incident(
    dataset_id: int,
    incident_id: int,
    db: Session = Depends(get_db),
) -> LLMSummaryResponse:
    with db.begin():
        get_dataset_or_404(db, dataset_id)
        summary = generate_and_store_summary(
            db,
            incident_id,
            dataset_id=dataset_id,
            enforce_dataset_scope=True,
        )

    if summary is None:
        raise HTTPException(status_code=404, detail="Incident not found in this dataset")
    return LLMSummaryResponse.model_validate(summary)


@router.get("/incidents/{incident_id}/summary", response_model=LLMSummaryResponse)
def get_dataset_incident_summary(
    dataset_id: int,
    incident_id: int,
    db: Session = Depends(get_db),
) -> LLMSummaryResponse:
    get_dataset_or_404(db, dataset_id)
    if load_dataset_incident(db, dataset_id, incident_id, include_evidence=False) is None:
        raise HTTPException(status_code=404, detail="Incident not found in this dataset")

    summary = get_latest_summary(db, incident_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return LLMSummaryResponse.model_validate(summary)


@router.get("/incidents/{incident_id}/report")
def export_dataset_incident_report(
    dataset_id: int,
    incident_id: int,
    db: Session = Depends(get_db),
) -> Response:
    get_dataset_or_404(db, dataset_id)
    report = generate_incident_markdown_report(
        db,
        incident_id,
        dataset_id=dataset_id,
        enforce_dataset_scope=True,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Incident not found in this dataset")

    filename = f"dataset-{dataset_id}-incident-{incident_id}-report.md"
    return Response(
        content=report,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def get_dataset_or_404(db: Session, dataset_id: int) -> UploadedDataset:
    dataset = db.get(UploadedDataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Uploaded dataset not found")
    return dataset


def load_dataset_incident(
    db: Session,
    dataset_id: int,
    incident_id: int,
    include_evidence: bool = True,
) -> Incident | None:
    statement = select(Incident).where(
        Incident.id == incident_id,
        Incident.dataset_id == dataset_id,
    )
    if include_evidence:
        statement = statement.options(
            selectinload(Incident.alerts),
            selectinload(Incident.event_links).selectinload(IncidentEvent.normalized_event),
        )
    return db.scalar(statement)
