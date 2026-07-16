from __future__ import annotations

import json
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.db.models import (
    DatasetFieldMapping,
    NormalizedEvent,
    RawEvent,
    UploadedDataset,
    UploadedFile,
)
from app.main import create_app
from app.uploads.mapping import (
    MappingDefinition,
    MappingValidationError,
    build_mapping_rules,
    get_dataset_mappings,
    inspect_records_schema,
    preview_dataset_records,
    replace_dataset_mappings,
    suggest_target_field,
    validate_mapping_definitions,
)
from app.uploads.normalize import normalize_uploaded_record
from app.uploads.parser import parse_upload_records
from app.uploads.service import normalize_uploaded_dataset

NOW = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)

ENTRA_RECORD = {
    "activityDateTime": "2026-07-15T14:00:00Z",
    "userPrincipalName": "alex.morgan@example.test",
    "ipAddress": "203.0.113.41",
    "appDisplayName": "Microsoft 365 Portal",
    "riskEventType": "unfamiliarFeatures",
    "deviceDetail": {"displayName": "LAPTOP-ALEX-01", "operatingSystem": "Windows"},
    "status": {"errorCode": 0, "failureReason": "None"},
}

CLOUDTRAIL_RECORD = {
    "eventTime": "2026-07-15T15:00:00Z",
    "eventSource": "iam.amazonaws.com",
    "eventName": "AttachUserPolicy",
    "sourceIPAddress": "198.51.100.24",
    "userIdentity": {
        "type": "IAMUser",
        "userName": "cloud-admin-example",
        "arn": "arn:aws:iam::123456789012:user/cloud-admin-example",
    },
    "requestParameters": {"policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"},
}


def test_csv_schema_detection() -> None:
    content = (
        "event_time,user,src_ip,hostname,action\n"
        "2026-07-15T14:00:00Z,alex.morgan,203.0.113.41,LAPTOP-ALEX-01,login\n"
    ).encode()
    records = parse_upload_records("entra.csv", content)
    fields = inspect_records_schema(records)

    assert {field.source_field for field in fields} == {
        "event_time", "user", "src_ip", "hostname", "action"
    }
    assert next(field for field in fields if field.source_field == "src_ip").sample_values == [
        "203.0.113.41"
    ]


def test_json_schema_detection() -> None:
    records = parse_upload_records("cloudtrail.json", json.dumps([CLOUDTRAIL_RECORD]).encode())
    fields = inspect_records_schema(records)

    assert "eventTime" in {field.source_field for field in fields}
    assert "eventName" in {field.source_field for field in fields}


def test_ndjson_schema_detection() -> None:
    content = "\n".join(
        [json.dumps(CLOUDTRAIL_RECORD), json.dumps({**CLOUDTRAIL_RECORD, "eventName": "ListUsers"})]
    ).encode()
    records = parse_upload_records("cloudtrail.ndjson", content)
    fields = inspect_records_schema(records)

    assert len(records) == 2
    assert "userIdentity.userName" in {field.source_field for field in fields}


def test_nested_json_uses_dotted_paths() -> None:
    fields = inspect_records_schema([ENTRA_RECORD, CLOUDTRAIL_RECORD])
    source_fields = {field.source_field for field in fields}

    assert "deviceDetail.displayName" in source_fields
    assert "status.failureReason" in source_fields
    assert "userIdentity.userName" in source_fields
    assert "requestParameters.policyArn" in source_fields


def test_automatic_mapping_suggestions_are_confidence_labeled() -> None:
    assert suggest_target_field("published") == ("timestamp", "high")
    assert suggest_target_field("userPrincipalName") == ("username", "high")
    assert suggest_target_field("client.ipAddress") == ("source_ip", "high")
    assert suggest_target_field("device.hostname") == ("asset", "high")
    assert suggest_target_field("eventName") == ("action", "high")
    assert suggest_target_field("custom.vendor.value") == (None, None)


def test_saving_and_retrieving_mappings_is_isolated_by_dataset(tmp_path: Path) -> None:
    dataset_a = stored_dataset(tmp_path, 1, "entra.json", [ENTRA_RECORD])
    dataset_b = stored_dataset(tmp_path, 2, "cloudtrail.json", [CLOUDTRAIL_RECORD])
    session = FakeMappingSession([dataset_a, dataset_b])

    schema_a = inspect_records_schema([ENTRA_RECORD])
    schema_b = inspect_records_schema([CLOUDTRAIL_RECORD])
    replace_dataset_mappings(
        session,  # type: ignore[arg-type]
        dataset_a,
        [MappingDefinition("userPrincipalName", "username")],
        schema_a,
    )
    replace_dataset_mappings(
        session,  # type: ignore[arg-type]
        dataset_b,
        [MappingDefinition("userIdentity.userName", "username")],
        schema_b,
    )

    assert [item.source_field for item in get_dataset_mappings(session, 1)] == [
        "userPrincipalName"
    ]
    assert [item.source_field for item in get_dataset_mappings(session, 2)] == [
        "userIdentity.userName"
    ]


def test_mapping_preview_does_not_insert_database_records(tmp_path: Path) -> None:
    dataset = stored_dataset(tmp_path, 1, "entra.json", [ENTRA_RECORD])
    session = FakeMappingSession([dataset])
    before_adds = session.add_count

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    response = TestClient(app).post(
        "/uploads/1/mapping-preview",
        json={
            "mappings": [
                {"source_field": "activityDateTime", "target_field": "timestamp"},
                {"source_field": "userPrincipalName", "target_field": "username"},
            ],
            "limit": 2,
        },
    )

    assert response.status_code == 200
    assert response.json()["records"][0]["username"] == "alex.morgan@example.test"
    assert session.add_count == before_adds
    assert session.raw_events == []
    assert session.normalized_events == []


def test_normalization_uses_persisted_explicit_mappings(tmp_path: Path) -> None:
    dataset = stored_dataset(tmp_path, 1, "entra.json", [ENTRA_RECORD])
    session = FakeMappingSession([dataset])
    session.add(
        DatasetFieldMapping(
            dataset_id=1,
            source_field="activityDateTime",
            target_field="timestamp",
            transformation_type="direct",
        )
    )
    session.add(
        DatasetFieldMapping(
            dataset_id=1,
            source_field="deviceDetail.displayName",
            target_field="asset",
            transformation_type="uppercase",
        )
    )

    result = normalize_uploaded_dataset(session, dataset)  # type: ignore[arg-type]

    assert result.normalized_inserted == 1
    assert session.normalized_events[0].asset == "LAPTOP-ALEX-01"
    assert session.normalized_events[0].event_timestamp == NOW
    assert session.raw_events[0].raw_payload["deviceDetail"]["displayName"] == "LAPTOP-ALEX-01"


def test_missing_optional_fields_do_not_fail() -> None:
    record = {"published": "2026-07-15T14:00:00Z"}
    normalized = normalize_uploaded_record(record, "generic")

    assert normalized.timestamp == NOW
    assert normalized.source_system == "uploaded_generic"
    assert normalized.event_type == "uploaded_event"
    assert normalized.username is None
    assert normalized.destination_ip is None


def test_invalid_target_and_duplicate_mappings_are_rejected() -> None:
    fields = {"eventTime", "eventName", "userIdentity.userName"}

    with pytest.raises(MappingValidationError, match="Invalid target field"):
        validate_mapping_definitions(
            [MappingDefinition("eventTime", "not_a_target")],
            fields,
        )

    with pytest.raises(MappingValidationError, match="Duplicate target"):
        validate_mapping_definitions(
            [
                MappingDefinition("eventTime", "timestamp"),
                MappingDefinition("eventName", "timestamp"),
            ],
            fields,
        )

    with pytest.raises(MappingValidationError, match="Duplicate source"):
        validate_mapping_definitions(
            [
                MappingDefinition("eventName", "action"),
                MappingDefinition("eventName", "event_type"),
            ],
            fields,
        )


def test_mapping_api_saves_and_returns_confirmed_mappings(tmp_path: Path) -> None:
    dataset = stored_dataset(tmp_path, 1, "cloudtrail.json", [CLOUDTRAIL_RECORD])
    session = FakeMappingSession([dataset])
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)

    schema_response = client.get("/uploads/1/schema")
    save_response = client.put(
        "/uploads/1/mappings",
        json={
            "mappings": [
                {"source_field": "eventTime", "target_field": "timestamp"},
                {"source_field": "eventName", "target_field": "action"},
                {"source_field": "userIdentity.userName", "target_field": "username"},
                {"source_field": "requestParameters.policyArn", "target_field": None},
            ]
        },
    )
    get_response = client.get("/uploads/1/mappings")

    assert schema_response.status_code == 200
    assert save_response.status_code == 200
    assert {item["target_field"] for item in get_response.json()} == {
        "timestamp", "action", "username"
    }
    assert dataset.status == "ready_to_normalize"


def stored_dataset(
    tmp_path: Path,
    dataset_id: int,
    filename: str,
    records: list[dict[str, Any]],
) -> UploadedDataset:
    path = tmp_path / f"{dataset_id}-{filename}"
    path.write_text(json.dumps(records), encoding="utf-8")
    dataset = UploadedDataset(
        id=dataset_id,
        name=f"Dataset {dataset_id}",
        description=None,
        created_at=NOW,
        status="mapping_required",
        source_type="cloud" if "cloudtrail" in filename else "auth",
        record_count=len(records),
    )
    dataset.files = [
        UploadedFile(
            id=dataset_id,
            dataset_id=dataset_id,
            original_filename=filename,
            stored_path=str(path),
            content_type="application/json",
            size_bytes=path.stat().st_size,
            uploaded_at=NOW,
        )
    ]
    return dataset


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def all(self) -> list[Any]:
        return self.items


class FakeMappingSession:
    def __init__(self, datasets: list[UploadedDataset]) -> None:
        self.datasets = {dataset.id: dataset for dataset in datasets}
        self.mappings: list[DatasetFieldMapping] = []
        self.raw_events: list[RawEvent] = []
        self.normalized_events: list[NormalizedEvent] = []
        self.next_id = 100
        self.add_count = 0

    def begin(self):
        return nullcontext()

    def get(self, model, primary_key: int, options=None):
        if model is UploadedDataset:
            return self.datasets.get(primary_key)
        return None

    def add(self, item: Any) -> None:
        self.add_count += 1
        if getattr(item, "id", None) is None:
            item.id = self.next_id
            self.next_id += 1
        if isinstance(item, DatasetFieldMapping):
            self.mappings.append(item)
        elif isinstance(item, RawEvent):
            self.raw_events.append(item)
        elif isinstance(item, NormalizedEvent):
            self.normalized_events.append(item)

    def delete(self, item: Any) -> None:
        if isinstance(item, DatasetFieldMapping):
            self.mappings.remove(item)

    def flush(self) -> None:
        return None

    def scalars(self, statement) -> FakeScalarResult:
        entity = statement.column_descriptions[0].get("entity")
        if entity is DatasetFieldMapping:
            dataset_id = next(
                (
                    value
                    for key, value in statement.compile().params.items()
                    if key.startswith("dataset_id")
                ),
                None,
            )
            return FakeScalarResult(
                [mapping for mapping in self.mappings if mapping.dataset_id == dataset_id]
            )
        if entity is NormalizedEvent:
            return FakeScalarResult(list(self.normalized_events))
        return FakeScalarResult([])

    def scalar(self, statement):
        return None
