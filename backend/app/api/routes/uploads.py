from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.api.schemas import UploadedDatasetResponse, WorkflowResponse
from app.core.config import get_settings
from app.db.models import UploadedDataset
from app.detections.engine import run_detections
from app.incidents.engine import run_incident_correlation
from app.uploads.parser import UploadParseError
from app.uploads.service import (
    create_missing_summaries_for_dataset,
    create_uploaded_dataset,
    normalize_uploaded_dataset,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


def get_upload_dir() -> Path:
    return Path(get_settings().upload_dir)


@router.post("", response_model=UploadedDatasetResponse)
async def upload_log_file(
    name: str = Form(...),
    source_type: str = Form("generic"),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadedDataset:
    if not name.strip():
        raise HTTPException(status_code=400, detail="Dataset name is required")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    content = await file.read()

    try:
        with db.begin():
            dataset = create_uploaded_dataset(
                session=db,
                upload_dir=get_upload_dir(),
                name=name,
                description=description,
                source_type=source_type,
                original_filename=file.filename,
                content_type=file.content_type,
                content=content,
            )
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return dataset


@router.get("", response_model=list[UploadedDatasetResponse])
def list_uploads(db: Session = Depends(get_db)) -> list[UploadedDataset]:
    statement = (
        select(UploadedDataset)
        .options(selectinload(UploadedDataset.files))
        .order_by(UploadedDataset.created_at.desc(), UploadedDataset.id.desc())
    )
    return list(db.scalars(statement).all())


@router.get("/{dataset_id}", response_model=UploadedDatasetResponse)
def get_upload(dataset_id: int, db: Session = Depends(get_db)) -> UploadedDataset:
    return get_dataset_or_404(dataset_id, db)


@router.post("/{dataset_id}/normalize", response_model=WorkflowResponse)
def normalize_upload(dataset_id: int, db: Session = Depends(get_db)) -> WorkflowResponse:
    try:
        with db.begin():
            dataset = get_dataset_or_404(dataset_id, db)
            result = normalize_uploaded_dataset(db, dataset)
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return WorkflowResponse(
        status="success",
        message="Uploaded dataset normalized",
        details={
            "dataset_id": dataset.id,
            "processed": result.processed,
            "raw_inserted": result.raw_inserted,
            "normalized_inserted": result.normalized_inserted,
            "skipped_existing": result.skipped_existing,
        },
    )


@router.post("/{dataset_id}/run-workflow", response_model=WorkflowResponse)
def run_upload_workflow(dataset_id: int, db: Session = Depends(get_db)) -> WorkflowResponse:
    try:
        with db.begin():
            dataset = get_dataset_or_404(dataset_id, db)
            etl_result = normalize_uploaded_dataset(db, dataset)
            detection_result = run_detections(db, dataset_id=dataset.id)
            incident_result = run_incident_correlation(db, dataset_id=dataset.id)
            summary_result = create_missing_summaries_for_dataset(db, dataset.id)
            dataset.status = "workflow_complete"
    except UploadParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return WorkflowResponse(
        status="success",
        message="Uploaded dataset workflow completed",
        details={
            "dataset_id": dataset.id,
            "etl": {
                "processed": etl_result.processed,
                "raw_inserted": etl_result.raw_inserted,
                "normalized_inserted": etl_result.normalized_inserted,
                "skipped_existing": etl_result.skipped_existing,
            },
            "detections": {
                "events_analyzed": detection_result.events_analyzed,
                "alerts_created": detection_result.alerts_created,
                "alerts_skipped": detection_result.alerts_skipped,
            },
            "incidents": {
                "alerts_analyzed": incident_result.alerts_analyzed,
                "incidents_created": incident_result.incidents_created,
                "alerts_linked": incident_result.alerts_linked,
                "incident_events_linked": incident_result.incident_events_linked,
            },
            "summaries": {
                "incidents_checked": summary_result.incidents_checked,
                "summaries_created": summary_result.summaries_created,
            },
        },
    )


def get_dataset_or_404(dataset_id: int, db: Session) -> UploadedDataset:
    dataset = db.get(
        UploadedDataset,
        dataset_id,
        options=[selectinload(UploadedDataset.files)],
    )

    if dataset is None:
        raise HTTPException(status_code=404, detail="Uploaded dataset not found")

    return dataset
