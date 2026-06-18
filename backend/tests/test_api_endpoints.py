from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.routes import workflow as workflow_routes
from app.db.models import Alert, Incident, IncidentEvent, NormalizedEvent
from app.main import create_app

NOW = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)


@pytest.fixture
def fake_session() -> "FakeSession":
    event = sample_event()
    alert = sample_alert()
    incident = sample_incident(alert=alert, event=event)

    return FakeSession(
        events={event.id: event},
        alerts={alert.id: alert},
        incidents={incident.id: incident},
    )


@pytest.fixture
def client(fake_session: "FakeSession") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: fake_session
    return TestClient(app)


def test_get_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_events(client: TestClient) -> None:
    response = client.get("/events?username=alex.morgan&limit=10")

    assert response.status_code == 200
    assert response.json()[0]["username"] == "alex.morgan"


def test_get_alerts(client: TestClient) -> None:
    response = client.get("/alerts?severity=high")

    assert response.status_code == 200
    assert response.json()[0]["alert_rule_name"] == "Suspicious API data download"


def test_get_incidents(client: TestClient) -> None:
    response = client.get("/incidents?status=open")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "High security incident for alex.morgan"


def test_get_incident_detail_includes_alerts_and_events(client: TestClient) -> None:
    response = client.get("/incidents/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["alerts"][0]["id"] == 1
    assert payload["related_events"][0]["id"] == 1


def test_missing_event_alert_and_incident_return_404(client: TestClient) -> None:
    assert client.get("/events/999").status_code == 404
    assert client.get("/alerts/999").status_code == 404
    assert client.get("/incidents/999").status_code == 404


def test_workflow_endpoints_return_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(workflow_routes, "default_data_dir", lambda: Path("data"))
    monkeypatch.setattr(
        workflow_routes,
        "run_etl",
        lambda data_dir, session: SimpleNamespace(
            processed=49,
            raw_inserted=49,
            normalized_inserted=49,
            skipped_existing=0,
        ),
    )
    monkeypatch.setattr(
        workflow_routes,
        "run_detections",
        lambda session: SimpleNamespace(
            events_analyzed=49,
            alerts_created=8,
            alerts_skipped=0,
        ),
    )
    monkeypatch.setattr(
        workflow_routes,
        "run_incident_correlation",
        lambda session: SimpleNamespace(
            alerts_analyzed=8,
            incidents_created=1,
            alerts_linked=8,
            incident_events_linked=12,
        ),
    )

    for path in (
        "/workflow/etl",
        "/workflow/detections",
        "/workflow/incidents",
        "/workflow/run-all",
    ):
        response = client.post(path)
        assert response.status_code == 200
        assert response.json()["status"] == "success"


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def all(self) -> list[Any]:
        return self.items


class FakeSession:
    def __init__(
        self,
        events: dict[int, NormalizedEvent],
        alerts: dict[int, Alert],
        incidents: dict[int, Incident],
    ) -> None:
        self.events = events
        self.alerts = alerts
        self.incidents = incidents

    def scalars(self, statement) -> FakeScalarResult:
        entity = statement.column_descriptions[0]["entity"]

        if entity is NormalizedEvent:
            return FakeScalarResult(list(self.events.values()))
        if entity is Alert:
            return FakeScalarResult(list(self.alerts.values()))
        if entity is Incident:
            return FakeScalarResult(list(self.incidents.values()))

        return FakeScalarResult([])

    def get(self, model, primary_key: int, options=None):
        if model is NormalizedEvent:
            return self.events.get(primary_key)
        if model is Alert:
            return self.alerts.get(primary_key)
        if model is Incident:
            return self.incidents.get(primary_key)

        return None

    def begin(self):
        return nullcontext()


def sample_event() -> NormalizedEvent:
    return NormalizedEvent(
        id=1,
        raw_event_id=1,
        normalized_at=NOW,
        event_timestamp=NOW,
        source_system="api_gateway",
        event_type="bulk_export",
        username="alex.morgan",
        source_ip="10.8.14.23",
        destination_ip=None,
        asset="API-GATEWAY-01",
        action="GET /api/v1/customers/export?region=all",
        outcome="200",
        severity=None,
        mitre_technique_id=None,
        normalized_message="Large API export",
    )


def sample_alert() -> Alert:
    return Alert(
        id=1,
        normalized_event_id=1,
        incident_id=1,
        created_at=NOW,
        alert_rule_name="Suspicious API data download",
        severity="high",
        description="alex.morgan performed suspicious API download",
        related_username="alex.morgan",
        related_asset="API-GATEWAY-01",
        related_event_ids=[1],
        mitre_technique_id="T1530",
        first_seen=NOW,
        last_seen=NOW,
        normalized_message="alex.morgan performed suspicious API download",
    )


def sample_incident(alert: Alert, event: NormalizedEvent) -> Incident:
    incident = Incident(
        id=1,
        created_at=NOW,
        updated_at=NOW,
        status="open",
        severity="high",
        title="High security incident for alex.morgan",
        suspected_attack_path="Suspicious API data download",
        description="Correlated API exfiltration alert",
        affected_user="alex.morgan",
        affected_assets=["API-GATEWAY-01"],
        first_seen=NOW,
        last_seen=NOW,
    )
    incident.alerts = [alert]
    incident.event_links = [
        IncidentEvent(
            id=1,
            incident_id=1,
            normalized_event_id=1,
            linked_at=NOW,
            normalized_event=event,
        )
    ]
    return incident
