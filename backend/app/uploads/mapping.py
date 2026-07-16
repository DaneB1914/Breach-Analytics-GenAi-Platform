from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DatasetFieldMapping, UploadedDataset
from app.etl.schemas import NormalizedRecord
from app.uploads.normalize import FieldMappingRule, normalize_uploaded_record
from app.uploads.parser import parse_upload_records

TARGET_FIELDS = (
    "timestamp",
    "source_system",
    "event_type",
    "username",
    "source_ip",
    "destination_ip",
    "asset",
    "action",
    "outcome",
    "severity",
    "mitre_technique_id",
    "message",
)
REQUIRED_TARGET_FIELDS = ("timestamp",)
OPTIONAL_TARGET_FIELDS = tuple(field for field in TARGET_FIELDS if field not in REQUIRED_TARGET_FIELDS)
TRANSFORMATION_TYPES = {"direct", "lowercase", "uppercase"}
MAPPING_EDITABLE_STATUSES = {"uploaded", "mapping_required", "ready_to_normalize", "failed"}
MAX_SCHEMA_RECORDS = 100
MAX_SAMPLE_VALUES = 3
MAX_PREVIEW_RECORDS = 10

SUGGESTION_ALIASES = {
    "timestamp": {
        "timestamp", "time", "event_time", "eventTime", "activityDateTime",
        "published", "createdDateTime", "observed_at", "datetime",
    },
    "source_system": {
        "source_system", "source", "system", "log_source", "product",
        "eventSource", "service", "appDisplayName",
    },
    "event_type": {
        "event_type", "type", "event_name", "request_category", "alert_type",
        "category", "riskEventType",
    },
    "username": {
        "username", "user", "user_name", "account", "actor", "userPrincipalName",
        "principal", "src_user", "actor.alternateId", "userIdentity.userName",
    },
    "source_ip": {
        "source_ip", "src_ip", "client_ip", "ipAddress", "sourceIPAddress",
        "client.ipAddress", "remote_ip", "ip", "sourceAddress",
    },
    "destination_ip": {
        "destination_ip", "dest_ip", "dst_ip", "target_ip",
        "assigned_private_ip", "server_ip",
    },
    "asset": {
        "asset", "host", "hostname", "device", "computer", "device_name",
        "device.hostname", "deviceDetail.displayName", "target_resource", "resource",
    },
    "action": {
        "action", "operation", "operationName", "activity", "eventName", "event_action",
    },
    "outcome": {
        "outcome", "result", "status", "status_code", "response_code",
        "errorCode", "status.errorCode", "status.failureReason",
    },
    "severity": {"severity", "level", "risk", "priority", "riskLevelDuringSignIn"},
    "mitre_technique_id": {
        "mitre_technique_id", "technique_id", "mitre", "technique",
    },
    "message": {"message", "reason", "description", "details", "alert", "failureReason"},
}


class MappingValidationError(ValueError):
    """Raised when submitted field mappings are invalid."""


class MappingLockedError(ValueError):
    """Raised when mappings are changed after normalization."""


@dataclass(frozen=True)
class SourceFieldSchema:
    source_field: str
    sample_values: list[str]
    suggested_target_field: str | None
    confidence: str | None


@dataclass(frozen=True)
class MappingDefinition:
    source_field: str
    target_field: str
    transformation_type: str = "direct"
    default_value: str | None = None


@dataclass(frozen=True)
class PreviewRecord:
    record_number: int
    normalized: NormalizedRecord


def load_dataset_records(
    dataset: UploadedDataset,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for uploaded_file in dataset.files:
        content = Path(uploaded_file.stored_path).read_bytes()
        file_records = parse_upload_records(uploaded_file.original_filename, content)
        for record in file_records:
            records.append(record)
            if limit is not None and len(records) >= limit:
                return records
    return records


def inspect_dataset_schema(dataset: UploadedDataset) -> list[SourceFieldSchema]:
    records = load_dataset_records(dataset, limit=MAX_SCHEMA_RECORDS)
    return inspect_records_schema(records)


def inspect_records_schema(records: Iterable[dict[str, Any]]) -> list[SourceFieldSchema]:
    samples: dict[str, list[str]] = {}
    for record in records:
        for field, value in flatten_record(record).items():
            rendered = render_sample_value(value)
            field_samples = samples.setdefault(field, [])
            if rendered not in field_samples and len(field_samples) < MAX_SAMPLE_VALUES:
                field_samples.append(rendered)

    candidates: list[SourceFieldSchema] = []
    for field in sorted(samples, key=str.lower):
        target, confidence = suggest_target_field(field)
        candidates.append(
            SourceFieldSchema(
                source_field=field,
                sample_values=samples[field],
                suggested_target_field=target,
                confidence=confidence,
            )
        )

    return remove_duplicate_target_suggestions(candidates)


def flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in record.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(flatten_record(value, path))
        else:
            flattened[path] = value
    return flattened


def render_sample_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        rendered = json.dumps(value, sort_keys=True, default=str)
    elif value is None:
        rendered = "null"
    else:
        rendered = str(value)
    return rendered if len(rendered) <= 160 else f"{rendered[:157]}..."


def suggest_target_field(source_field: str) -> tuple[str | None, str | None]:
    normalized_full = normalize_field_name(source_field)
    normalized_leaf = normalize_field_name(source_field.split(".")[-1])

    # Prefer an exact alias before applying punctuation/case normalization. This
    # keeps vendor fields such as eventName mapped to action while event_name can
    # still represent an event type.
    for target_field, aliases in SUGGESTION_ALIASES.items():
        if source_field in aliases:
            return target_field, "high"

    for target_field, aliases in SUGGESTION_ALIASES.items():
        normalized_aliases = {normalize_field_name(alias) for alias in aliases}
        if normalized_full in normalized_aliases:
            return target_field, "high"
        if "." in source_field and normalized_leaf in normalized_aliases:
            return target_field, "medium"

    return None, None


def normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def remove_duplicate_target_suggestions(
    fields: list[SourceFieldSchema],
) -> list[SourceFieldSchema]:
    selected_sources: dict[str, str] = {}
    ranked = sorted(
        (field for field in fields if field.suggested_target_field),
        key=lambda field: (
            0 if field.confidence == "high" else 1,
            0 if normalize_field_name(field.source_field) == normalize_field_name(field.suggested_target_field or "") else 1,
            field.source_field.lower(),
        ),
    )
    for field in ranked:
        selected_sources.setdefault(field.suggested_target_field or "", field.source_field)

    return [
        field
        if not field.suggested_target_field
        or selected_sources.get(field.suggested_target_field) == field.source_field
        else SourceFieldSchema(field.source_field, field.sample_values, None, None)
        for field in fields
    ]


def schema_has_timestamp_mapping(fields: Iterable[SourceFieldSchema]) -> bool:
    return any(field.suggested_target_field == "timestamp" for field in fields)


def get_dataset_mappings(session: Session, dataset_id: int) -> list[DatasetFieldMapping]:
    statement = (
        select(DatasetFieldMapping)
        .where(DatasetFieldMapping.dataset_id == dataset_id)
        .order_by(DatasetFieldMapping.source_field)
    )
    return list(session.scalars(statement).all())


def mapping_definitions_from_models(
    mappings: Iterable[DatasetFieldMapping],
) -> list[MappingDefinition]:
    return [
        MappingDefinition(
            source_field=mapping.source_field,
            target_field=mapping.target_field,
            transformation_type=mapping.transformation_type,
            default_value=mapping.default_value,
        )
        for mapping in mappings
    ]


def validate_mapping_definitions(
    definitions: Iterable[MappingDefinition],
    available_source_fields: set[str],
) -> list[MappingDefinition]:
    cleaned: list[MappingDefinition] = []
    seen_sources: set[str] = set()
    seen_targets: set[str] = set()

    for definition in definitions:
        source_field = definition.source_field.strip()
        target_field = definition.target_field.strip()
        transformation_type = definition.transformation_type.strip().lower() or "direct"

        if not source_field:
            raise MappingValidationError("source_field cannot be empty")
        if source_field not in available_source_fields:
            raise MappingValidationError(f"Unknown source field: {source_field}")
        if target_field not in TARGET_FIELDS:
            raise MappingValidationError(f"Invalid target field: {target_field}")
        if transformation_type not in TRANSFORMATION_TYPES:
            raise MappingValidationError(
                f"Invalid transformation_type: {transformation_type}"
            )
        if source_field in seen_sources:
            raise MappingValidationError(f"Duplicate source field mapping: {source_field}")
        if target_field in seen_targets:
            raise MappingValidationError(f"Duplicate target field mapping: {target_field}")

        seen_sources.add(source_field)
        seen_targets.add(target_field)
        cleaned.append(
            MappingDefinition(
                source_field=source_field,
                target_field=target_field,
                transformation_type=transformation_type,
                default_value=definition.default_value,
            )
        )

    return cleaned


def replace_dataset_mappings(
    session: Session,
    dataset: UploadedDataset,
    definitions: list[MappingDefinition],
    schema: list[SourceFieldSchema],
) -> list[DatasetFieldMapping]:
    if dataset.status not in MAPPING_EDITABLE_STATUSES:
        raise MappingLockedError(
            "Field mappings are locked after normalization to preserve auditability."
        )

    for existing in get_dataset_mappings(session, dataset.id):
        session.delete(existing)

    created: list[DatasetFieldMapping] = []
    for definition in definitions:
        mapping = DatasetFieldMapping(
            dataset_id=dataset.id,
            source_field=definition.source_field,
            target_field=definition.target_field,
            transformation_type=definition.transformation_type,
            default_value=definition.default_value,
        )
        session.add(mapping)
        created.append(mapping)

    has_timestamp = any(item.target_field == "timestamp" for item in definitions)
    dataset.status = (
        "ready_to_normalize"
        if has_timestamp or schema_has_timestamp_mapping(schema)
        else "mapping_required"
    )
    session.flush()
    return created


def build_mapping_rules(
    definitions: Iterable[MappingDefinition],
) -> dict[str, FieldMappingRule]:
    return {
        definition.target_field: FieldMappingRule(
            source_field=definition.source_field,
            transformation_type=definition.transformation_type,
            default_value=definition.default_value,
        )
        for definition in definitions
    }


def preview_dataset_records(
    dataset: UploadedDataset,
    definitions: list[MappingDefinition],
    limit: int,
) -> tuple[list[PreviewRecord], list[str]]:
    bounded_limit = max(1, min(limit, MAX_PREVIEW_RECORDS))
    records = load_dataset_records(dataset, limit=bounded_limit)
    rules = build_mapping_rules(definitions)
    previews: list[PreviewRecord] = []
    warnings: list[str] = []

    for index, record in enumerate(records, start=1):
        normalized = normalize_uploaded_record(record, dataset.source_type, rules)
        if normalized.timestamp is None:
            warnings.append(
                f"Record {index} has no valid timestamp and cannot be normalized until its mapping is corrected."
            )
        previews.append(PreviewRecord(record_number=index, normalized=normalized))

    return previews, warnings
