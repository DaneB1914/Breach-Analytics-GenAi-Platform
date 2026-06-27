from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.routes import uploads as upload_routes
from app.db.models import NormalizedEvent, RawEvent, UploadedDataset, UploadedFile
from app.main import create_app


@pytest.fixture
def upload_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, "FakeUploadSession"]:
    fake_session = FakeUploadSession()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: fake_session
    monkeypatch.setattr(upload_routes, "get_upload_dir", lambda: tmp_path)
    return TestClient(app), fake_session


def test_uploading_csv_creates_dataset(upload_client: tuple[TestClient, "FakeUploadSession"]) -> None:
    client, fake_session = upload_client

    response = client.post(
        "/uploads",
        data={"name": "Uploaded auth CSV", "source_type": "auth"},
        files={
            "file": (
                "auth_upload.csv",
                "timestamp,username,source_ip,action,outcome\n"
                "2026-06-24T10:00:00Z,alex.morgan,203.0.113.77,login,success\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Uploaded auth CSV"
    assert payload["record_count"] == 1
    assert payload["files"][0]["original_filename"] == "auth_upload.csv"
    assert len(fake_session.datasets) == 1


def test_uploading_json_creates_dataset(upload_client: tuple[TestClient, "FakeUploadSession"]) -> None:
    client, _ = upload_client

    response = client.post(
        "/uploads",
        data={"name": "Uploaded endpoint JSON", "source_type": "endpoint"},
        files={
            "file": (
                "endpoint_upload.json",
                '[{"timestamp":"2026-06-24T10:05:00Z","user_name":"alex.morgan","host":"LAPTOP-ALEX-01"}]',
                "application/json",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "endpoint"
    assert response.json()["record_count"] == 1


def test_rejects_unsupported_file_type(upload_client: tuple[TestClient, "FakeUploadSession"]) -> None:
    client, _ = upload_client

    response = client.post(
        "/uploads",
        data={"name": "Bad upload", "source_type": "generic"},
        files={"file": ("notes.txt", "not a supported log format", "text/plain")},
    )

    assert response.status_code == 400
    assert "supported" in response.json()["detail"].lower()


def test_normalizes_uploaded_records(upload_client: tuple[TestClient, "FakeUploadSession"]) -> None:
    client, fake_session = upload_client
    upload_response = client.post(
        "/uploads",
        data={"name": "Normalize me", "source_type": "auth"},
        files={
            "file": (
                "auth_upload.csv",
                "timestamp,username,source_ip,asset,action,outcome,severity\n"
                "2026-06-24T10:00:00Z,alex.morgan,203.0.113.77,CLOUD-IAM,login,success,medium\n",
                "text/csv",
            )
        },
    )

    dataset_id = upload_response.json()["id"]
    response = client.post(f"/uploads/{dataset_id}/normalize")

    assert response.status_code == 200
    assert response.json()["details"]["normalized_inserted"] == 1
    assert fake_session.raw_events[0].raw_payload["username"] == "alex.morgan"
    assert fake_session.normalized_events[0].username == "alex.morgan"
    assert fake_session.normalized_events[0].source_system == "CLOUD-IAM"
    assert fake_session.flush_count >= 2


def test_runs_workflow_for_uploaded_dataset(
    upload_client: tuple[TestClient, "FakeUploadSession"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, fake_session = upload_client
    upload_response = client.post(
        "/uploads",
        data={"name": "Workflow upload", "source_type": "auth"},
        files={
            "file": (
                "auth_upload.json",
                '[{"timestamp":"2026-06-24T10:00:00Z","username":"alex.morgan","source_ip":"203.0.113.77","action":"login","outcome":"success"}]',
                "application/json",
            )
        },
    )
    dataset_id = upload_response.json()["id"]

    monkeypatch.setattr(
        upload_routes,
        "run_detections",
        lambda db, dataset_id=None: SimpleNamespace(events_analyzed=1, alerts_created=1, alerts_skipped=0),
    )
    monkeypatch.setattr(
        upload_routes,
        "run_incident_correlation",
        lambda db, dataset_id=None: SimpleNamespace(
            alerts_analyzed=1,
            incidents_created=1,
            alerts_linked=1,
            incident_events_linked=1,
        ),
    )
    monkeypatch.setattr(
        upload_routes,
        "create_missing_summaries_for_dataset",
        lambda db, dataset_id: SimpleNamespace(incidents_checked=1, summaries_created=1),
    )

    response = client.post(f"/uploads/{dataset_id}/run-workflow")

    assert response.status_code == 200
    assert response.json()["message"] == "Uploaded dataset workflow completed"
    assert response.json()["details"]["detections"]["alerts_created"] == 1
    assert fake_session.datasets[dataset_id].status == "workflow_complete"


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def all(self) -> list[Any]:
        return self.items


class FakeUploadSession:
    def __init__(self) -> None:
        self.datasets: dict[int, UploadedDataset] = {}
        self.files: list[UploadedFile] = []
        self.raw_events: list[RawEvent] = []
        self.normalized_events: list[NormalizedEvent] = []
        self._next_id = 1
        self.flush_count = 0

    def begin(self):
        return nullcontext()

    def add(self, item: Any) -> None:
        if getattr(item, "id", None) is None:
            item.id = self._next_id
            self._next_id += 1

        if isinstance(item, UploadedDataset):
            self.datasets[item.id] = item
        elif isinstance(item, UploadedFile):
            self.files.append(item)
            dataset = self.datasets.get(item.dataset_id)
            if dataset is not None and item not in dataset.files:
                dataset.files.append(item)
        elif isinstance(item, RawEvent):
            self.raw_events.append(item)
        elif isinstance(item, NormalizedEvent):
            self.normalized_events.append(item)

    def flush(self) -> None:
        self.flush_count += 1
        return None

    def get(self, model, primary_key: int, options=None):
        if model is UploadedDataset:
            return self.datasets.get(primary_key)
        return None

    def scalars(self, statement) -> FakeScalarResult:
        entity = statement.column_descriptions[0].get("entity")
        if entity is UploadedDataset:
            return FakeScalarResult(list(self.datasets.values()))
        if entity is NormalizedEvent:
            return FakeScalarResult(list(self.normalized_events))
        return FakeScalarResult([])

    def scalar(self, statement):
        return None
