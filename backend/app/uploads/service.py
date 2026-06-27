from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.db.models import Incident, IncidentEvent, NormalizedEvent, RawEvent, UploadedDataset, UploadedFile
from app.etl.schemas import ETLResult, NormalizedRecord
from app.summaries.service import generate_and_store_summary, get_latest_summary
from app.uploads.normalize import normalize_uploaded_record
from app.uploads.parser import parse_upload_records, validate_source_type


@dataclass(frozen=True)
class UploadWorkflowSummaryResult:
    """Summary of automatically generated summaries for uploaded incidents."""

    incidents_checked: int
    summaries_created: int


def create_uploaded_dataset(
    session: Session,
    upload_dir: Path,
    name: str,
    description: str | None,
    source_type: str,
    original_filename: str,
    content_type: str | None,
    content: bytes,
) -> UploadedDataset:
    """Create dataset metadata, validate the file, and store the uploaded bytes."""

    cleaned_source_type = validate_source_type(source_type)
    records = parse_upload_records(original_filename, content)

    dataset = UploadedDataset(
        name=name.strip(),
        description=description.strip() if description else None,
        source_type=cleaned_source_type,
        status="uploaded",
        record_count=len(records),
    )
    session.add(dataset)
    session.flush()

    stored_path = store_uploaded_file(upload_dir, dataset.id, original_filename, content)
    uploaded_file = UploadedFile(
        dataset_id=dataset.id,
        original_filename=original_filename,
        stored_path=str(stored_path),
        content_type=content_type,
        size_bytes=len(content),
    )
    uploaded_file.dataset = dataset
    session.add(uploaded_file)
    session.flush()

    return dataset


def store_uploaded_file(upload_dir: Path, dataset_id: int, original_filename: str, content: bytes) -> Path:
    dataset_dir = upload_dir / f"dataset-{dataset_id}"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(original_filename)
    stored_path = dataset_dir / f"{uuid4().hex}_{safe_name}"
    stored_path.write_bytes(content)
    return stored_path


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name or "uploaded-log"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def normalize_uploaded_dataset(session: Session, dataset: UploadedDataset) -> ETLResult:
    """Parse stored upload files and load raw plus normalized events."""

    raw_inserted = 0
    normalized_inserted = 0
    skipped_existing = 0
    processed = 0

    for uploaded_file in dataset.files:
        content = Path(uploaded_file.stored_path).read_bytes()
        records = parse_upload_records(uploaded_file.original_filename, content)
        processed += len(records)

        for raw_record in records:
            normalized_record = normalize_uploaded_record(raw_record, dataset.source_type)
            raw_event = find_existing_uploaded_raw_event(
                session=session,
                dataset_id=dataset.id,
                normalized_record=normalized_record,
                raw_payload=raw_record,
            )

            if raw_event is None:
                raw_event = build_uploaded_raw_event(dataset.id, raw_record, normalized_record)
                session.add(raw_event)
                session.flush()
                raw_inserted += 1

            if uploaded_normalized_event_exists(session, raw_event.id):
                skipped_existing += 1
                continue

            session.add(build_uploaded_normalized_event(dataset.id, raw_event.id, normalized_record))
            normalized_inserted += 1

    dataset.record_count = processed
    dataset.status = "normalized"

    # Later workflow steps run in the same transaction with autoflush=False.
    # Flush so detections can see every uploaded normalized event.
    if raw_inserted or normalized_inserted:
        session.flush()

    return ETLResult(
        processed=processed,
        raw_inserted=raw_inserted,
        normalized_inserted=normalized_inserted,
        skipped_existing=skipped_existing,
    )


def find_existing_uploaded_raw_event(
    session: Session,
    dataset_id: int,
    normalized_record: NormalizedRecord,
    raw_payload: dict,
) -> RawEvent | None:
    statement = select(RawEvent).where(
        RawEvent.uploaded_dataset_id == dataset_id,
        RawEvent.source_system == normalized_record.source_system,
        RawEvent.event_type == normalized_record.event_type,
        RawEvent.raw_payload == raw_payload,
    )
    return session.scalar(statement)


def uploaded_normalized_event_exists(session: Session, raw_event_id: int) -> bool:
    statement = select(NormalizedEvent.id).where(NormalizedEvent.raw_event_id == raw_event_id)
    return session.scalar(statement) is not None


def build_uploaded_raw_event(
    dataset_id: int,
    raw_payload: dict,
    normalized_record: NormalizedRecord,
) -> RawEvent:
    return RawEvent(
        uploaded_dataset_id=dataset_id,
        event_timestamp=normalized_record.timestamp,
        source_system=normalized_record.source_system,
        event_type=normalized_record.event_type,
        raw_payload=raw_payload,
    )


def build_uploaded_normalized_event(
    dataset_id: int,
    raw_event_id: int,
    normalized_record: NormalizedRecord,
) -> NormalizedEvent:
    return NormalizedEvent(
        raw_event_id=raw_event_id,
        uploaded_dataset_id=dataset_id,
        event_timestamp=normalized_record.timestamp,
        source_system=normalized_record.source_system,
        event_type=normalized_record.event_type,
        username=normalized_record.username,
        source_ip=normalized_record.source_ip,
        destination_ip=normalized_record.destination_ip,
        asset=normalized_record.asset,
        action=normalized_record.action,
        outcome=normalized_record.outcome,
        severity=normalized_record.severity,
        mitre_technique_id=normalized_record.mitre_technique_id,
        normalized_message=normalized_record.message,
    )


def create_missing_summaries_for_dataset(
    session: Session,
    dataset_id: int,
) -> UploadWorkflowSummaryResult:
    """Generate mock/LLM summaries for incidents that include uploaded evidence."""

    incident_ids = list(
        session.scalars(
            select(distinct(Incident.id))
            .join(IncidentEvent, IncidentEvent.incident_id == Incident.id)
            .join(NormalizedEvent, NormalizedEvent.id == IncidentEvent.normalized_event_id)
            .where(NormalizedEvent.uploaded_dataset_id == dataset_id)
        ).all()
    )

    summaries_created = 0
    for incident_id in incident_ids:
        if get_latest_summary(session, incident_id) is not None:
            continue
        if generate_and_store_summary(session, incident_id) is not None:
            summaries_created += 1

    return UploadWorkflowSummaryResult(
        incidents_checked=len(incident_ids),
        summaries_created=summaries_created,
    )
