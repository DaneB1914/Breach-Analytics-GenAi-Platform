from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.db.models import (
    Alert,
    Incident,
    IncidentEvent,
    LLMSummary,
    NormalizedEvent,
    UploadedDataset,
)
from app.detections.engine import run_detections
from app.incidents.engine import run_incident_correlation
from app.main import create_app
from app.reports.service import generate_incident_markdown_report

NOW = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)


def test_dataset_endpoints_return_only_the_selected_dataset() -> None:
    session = IsolationSession(
        datasets=[dataset(1, "Dataset A"), dataset(2, "Dataset B")],
        events=[event(11, 1, "dataset-a.user"), event(22, 2, "dataset-b.user")],
    )
    client = create_client(session)

    dataset_a_events = client.get("/uploads/1/events").json()
    dataset_b_events = client.get("/uploads/2/events").json()

    assert [item["username"] for item in dataset_a_events] == ["dataset-a.user"]
    assert [item["username"] for item in dataset_b_events] == ["dataset-b.user"]
    assert client.get("/events").json() == []


def test_detection_correlation_and_reports_remain_dataset_scoped() -> None:
    dataset_a = dataset(1, "Dataset A")
    dataset_b = dataset(2, "Dataset B")
    event_a = event(11, 1, "dataset-a.user")
    event_b = event(22, 2, "dataset-b.user")
    session = IsolationSession(
        datasets=[dataset_a, dataset_b],
        events=[event_a, event_b],
    )

    detection_a = run_detections(session, dataset_id=dataset_a.id)  # type: ignore[arg-type]
    assert detection_a.events_analyzed == 1
    assert {item.dataset_id for item in session.alerts} == {dataset_a.id}
    assert {item.related_username for item in session.alerts} == {"dataset-a.user"}

    detection_b = run_detections(session, dataset_id=dataset_b.id)  # type: ignore[arg-type]
    assert detection_b.events_analyzed == 1
    assert {item.dataset_id for item in session.alerts} == {dataset_a.id, dataset_b.id}

    correlation_a = run_incident_correlation(session, dataset_id=dataset_a.id)  # type: ignore[arg-type]
    assert correlation_a.incidents_created == 1
    assert next(item for item in session.alerts if item.dataset_id == 2).incident_id is None

    correlation_b = run_incident_correlation(session, dataset_id=dataset_b.id)  # type: ignore[arg-type]
    assert correlation_b.incidents_created == 1
    assert {item.dataset_id for item in session.incidents} == {1, 2}
    assert all(
        {alert.dataset_id for alert in incident_item.alerts} == {incident_item.dataset_id}
        for incident_item in session.incidents
    )

    incident_a = next(item for item in session.incidents if item.dataset_id == 1)
    # Even if a bad legacy link exists, scoped evidence loading removes it.
    session.add(
        IncidentEvent(
            incident_id=incident_a.id,
            normalized_event_id=event_b.id,
        )
    )
    session.flush()

    report = generate_incident_markdown_report(
        session,  # type: ignore[arg-type]
        incident_a.id,
        dataset_id=dataset_a.id,
        enforce_dataset_scope=True,
    )
    assert report is not None
    assert "dataset-a.user" in report
    assert "dataset-b.user" not in report
    assert str(event_a.id) in report
    assert str(event_b.id) not in report

    client = create_client(session)
    assert len(client.get("/uploads/1/alerts").json()) == 1
    assert len(client.get("/uploads/2/alerts").json()) == 1
    assert len(client.get("/uploads/1/incidents").json()) == 1
    assert len(client.get("/uploads/2/incidents").json()) == 1
    assert client.get(f"/uploads/2/incidents/{incident_a.id}").status_code == 404
    assert client.post(f"/uploads/2/incidents/{incident_a.id}/summarize").status_code == 404
    assert client.get(f"/uploads/2/incidents/{incident_a.id}/summary").status_code == 404
    assert client.get(f"/uploads/2/incidents/{incident_a.id}/report").status_code == 404

    # Rerunning Dataset A skips its alerts and leaves Dataset B unchanged.
    dataset_b_incident_id = next(item.id for item in session.incidents if item.dataset_id == 2)
    rerun = run_detections(session, dataset_id=dataset_a.id)  # type: ignore[arg-type]
    assert rerun.alerts_created == 0
    assert next(item.id for item in session.incidents if item.dataset_id == 2) == dataset_b_incident_id


def create_client(session: "IsolationSession") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


def dataset(dataset_id: int, name: str) -> UploadedDataset:
    item = UploadedDataset(
        id=dataset_id,
        name=name,
        description=f"Isolated investigation for {name}",
        created_at=NOW,
        status="workflow_complete",
        source_type="endpoint",
        record_count=1,
    )
    item.files = []
    return item


def event(event_id: int, dataset_id: int, username: str) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        raw_event_id=event_id,
        dataset_id=dataset_id,
        normalized_at=NOW,
        event_timestamp=NOW + timedelta(minutes=event_id),
        source_system="endpoint-edr",
        event_type="credential_access",
        username=username,
        source_ip=None,
        destination_ip=None,
        asset=f"LAPTOP-{dataset_id}",
        action="alert",
        outcome="observed",
        severity="high",
        mitre_technique_id="T1003.001",
        normalized_message=f"Credential access activity for {username}",
    )


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def all(self) -> list[Any]:
        return self.items


class IsolationSession:
    """Small SQL-aware test double used to exercise dataset query filters."""

    def __init__(
        self,
        datasets: list[UploadedDataset],
        events: list[NormalizedEvent],
    ) -> None:
        self.datasets = {item.id: item for item in datasets}
        self.events = events
        self.alerts: list[Alert] = []
        self.incidents: list[Incident] = []
        self.incident_events: list[IncidentEvent] = []
        self.summaries: list[LLMSummary] = []
        self.next_id = 100

    def begin(self):
        return nullcontext()

    def get(self, model, primary_key: int, options=None):
        if model is UploadedDataset:
            return self.datasets.get(primary_key)
        if model is Incident:
            return next((item for item in self.incidents if item.id == primary_key), None)
        return None

    def add(self, item: Any) -> None:
        if getattr(item, "id", None) is None:
            item.id = self.next_id
            self.next_id += 1

        if isinstance(item, Alert):
            self.alerts.append(item)
        elif isinstance(item, Incident):
            item.alerts = []
            item.event_links = []
            item.llm_summaries = []
            self.incidents.append(item)
        elif isinstance(item, IncidentEvent):
            event_item = next(
                (event_record for event_record in self.events if event_record.id == item.normalized_event_id),
                None,
            )
            item.normalized_event = event_item
            self.incident_events.append(item)
        elif isinstance(item, LLMSummary):
            self.summaries.append(item)

    def flush(self) -> None:
        for incident_item in self.incidents:
            incident_item.alerts = [
                alert_item
                for alert_item in self.alerts
                if alert_item.incident_id == incident_item.id
            ]
            incident_item.event_links = [
                link
                for link in self.incident_events
                if link.incident_id == incident_item.id
            ]

    def scalars(self, statement) -> FakeScalarResult:
        entity = statement.column_descriptions[0].get("entity")
        if entity is NormalizedEvent:
            items: list[Any] = self._filter(self.events, statement, "uploaded_dataset_id")
        elif entity is Alert:
            items = self._filter(self.alerts, statement, "dataset_id")
        elif entity is Incident:
            items = self._filter(self.incidents, statement, "dataset_id")
        elif entity is LLMSummary:
            items = list(self.summaries)
        else:
            items = []

        params = statement.compile().params
        id_filter = params.get("id_1")
        if isinstance(id_filter, int):
            items = [item for item in items if item.id == id_filter]
        elif isinstance(id_filter, list):
            items = [item for item in items if item.id in id_filter]

        rule_name = params.get("alert_rule_name_1")
        if rule_name is not None:
            items = [item for item in items if item.alert_rule_name == rule_name]

        selected_expression = statement.column_descriptions[0].get("expr")
        if entity in (NormalizedEvent, Incident) and getattr(selected_expression, "key", None) == "id":
            items = [item.id for item in items]
        return FakeScalarResult(items)

    def scalar(self, statement):
        results = self.scalars(statement).all()
        if not results:
            return None
        if statement.column_descriptions[0].get("entity") is LLMSummary:
            return sorted(results, key=lambda item: (item.created_at, item.id))[-1]
        return results[0]

    @staticmethod
    def _filter(items: list[Any], statement, parameter_name: str) -> list[Any]:
        if not items:
            return []

        sql = str(statement)
        params = statement.compile().params
        table_name = items[0].__table__.name
        matching_parameter = next(
            (value for key, value in params.items() if key.startswith(parameter_name)),
            None,
        )

        if f"{table_name}.{parameter_name} IS NULL" in sql:
            return [item for item in items if item.dataset_id is None]
        if matching_parameter is not None:
            return [item for item in items if item.dataset_id == matching_parameter]
        return list(items)
