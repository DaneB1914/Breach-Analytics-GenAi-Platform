from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import NormalizedEvent, RawEvent
from app.etl.extract import extract_all_sources
from app.etl.normalize import normalize_extracted_record
from app.etl.schemas import ETLResult, ExtractedRecord, NormalizedRecord


def run_etl(data_dir, session: Session) -> ETLResult:
    """Extract records, normalize them, and load them into PostgreSQL."""

    extracted_records = extract_all_sources(data_dir)
    return load_extracted_records(extracted_records, session)


def load_extracted_records(
    extracted_records: list[ExtractedRecord],
    session: Session,
) -> ETLResult:
    raw_inserted = 0
    normalized_inserted = 0
    skipped_existing = 0

    for extracted_record in extracted_records:
        normalized_record = normalize_extracted_record(extracted_record)

        raw_event = find_existing_raw_event(
            session=session,
            normalized_record=normalized_record,
            raw_payload=extracted_record.raw_record,
        )

        if raw_event is None:
            raw_event = build_raw_event(
                raw_payload=extracted_record.raw_record,
                normalized_record=normalized_record,
            )
            session.add(raw_event)
            session.flush()
            raw_inserted += 1

        if normalized_event_exists(session, raw_event.id):
            skipped_existing += 1
            continue

        session.add(build_normalized_event(raw_event.id, normalized_record))
        normalized_inserted += 1

    return ETLResult(
        processed=len(extracted_records),
        raw_inserted=raw_inserted,
        normalized_inserted=normalized_inserted,
        skipped_existing=skipped_existing,
    )


def find_existing_raw_event(
    session: Session,
    normalized_record: NormalizedRecord,
    raw_payload: dict,
) -> RawEvent | None:
    # For this small portfolio dataset, matching the original payload is a simple
    # way to make repeated ETL runs idempotent without adding source-specific IDs.
    statement = select(RawEvent).where(
        RawEvent.source_system == normalized_record.source_system,
        RawEvent.event_type == normalized_record.event_type,
        RawEvent.raw_payload == raw_payload,
    )
    return session.scalar(statement)


def normalized_event_exists(session: Session, raw_event_id: int) -> bool:
    statement = select(NormalizedEvent.id).where(
        NormalizedEvent.raw_event_id == raw_event_id,
    )
    return session.scalar(statement) is not None


def build_raw_event(
    raw_payload: dict,
    normalized_record: NormalizedRecord,
) -> RawEvent:
    return RawEvent(
        event_timestamp=normalized_record.timestamp,
        source_system=normalized_record.source_system,
        event_type=normalized_record.event_type,
        raw_payload=raw_payload,
    )


def build_normalized_event(
    raw_event_id: int,
    normalized_record: NormalizedRecord,
) -> NormalizedEvent:
    return NormalizedEvent(
        raw_event_id=raw_event_id,
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
