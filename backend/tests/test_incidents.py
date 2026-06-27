from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.models import Alert, Incident, IncidentEvent
from app.incidents.correlation import build_incident, group_related_alerts
from app.incidents.engine import assign_alerts_to_incident, run_incident_correlation

BASE_TIME = datetime(2026, 6, 16, 8, 49, tzinfo=timezone.utc)


def test_groups_multiple_alerts_for_same_suspicious_user_into_one_incident() -> None:
    alerts = [
        alert(1, "Brute force followed by successful login", "high", "alex.morgan", "CLOUD-IAM", [1, 2, 3, 4]),
        alert(2, "VPN login followed by privilege escalation", "high", "alex.morgan", "CLOUD-IAM", [5, 6, 7]),
        alert(3, "Suspicious API data download", "high", "alex.morgan", "API-GATEWAY-01", [8]),
    ]

    groups = group_related_alerts(alerts)

    assert len(groups) == 1
    assert groups[0].affected_user == "alex.morgan"
    assert groups[0].affected_assets == ["API-GATEWAY-01", "CLOUD-IAM"]
    assert groups[0].related_event_ids == [1, 2, 3, 4, 5, 6, 7, 8]


def test_keeps_unrelated_users_and_assets_in_separate_incidents() -> None:
    alerts = [
        alert(1, "Successful login from unusual IP", "medium", "alex.morgan", "CLOUD-IAM", [1]),
        alert(2, "Endpoint malware or credential access", "high", "jamie.lee", "LAPTOP-JAMIE-01", [2]),
    ]

    groups = group_related_alerts(alerts)

    assert len(groups) == 2
    assert {group.affected_user for group in groups} == {"alex.morgan", "jamie.lee"}


def test_assigns_alert_incident_id_values() -> None:
    alerts = [
        alert(1, "Successful login from unusual IP", "medium", "alex.morgan", "CLOUD-IAM", [1]),
        alert(2, "Suspicious API data download", "high", "alex.morgan", "API-GATEWAY-01", [2]),
    ]
    group = group_related_alerts(alerts)[0]

    linked_count = assign_alerts_to_incident(group, incident_id=42)

    assert linked_count == 2
    assert [item.incident_id for item in alerts] == [42, 42]


def test_sets_incident_severity_from_highest_related_alert_severity() -> None:
    alerts = [
        alert(1, "Successful login from unusual IP", "medium", "alex.morgan", "CLOUD-IAM", [1]),
        alert(2, "Multiple high-severity events by same user within 24 hours", "critical", "alex.morgan", "LAPTOP-ALEX-01", [2, 3, 4]),
        alert(3, "Suspicious API data download", "high", "alex.morgan", "API-GATEWAY-01", [5]),
    ]
    group = group_related_alerts(alerts)[0]

    incident = build_incident(group)

    assert incident.severity == "critical"
    assert incident.title == "Critical security incident for alex.morgan"


def test_creates_readable_suspected_attack_path() -> None:
    alerts = [
        alert(1, "Brute force followed by successful login", "high", "alex.morgan", "CLOUD-IAM", [1, 2]),
        alert(2, "VPN login followed by privilege escalation", "high", "alex.morgan", "CLOUD-IAM", [3, 4]),
        alert(3, "Suspicious API data download", "high", "alex.morgan", "API-GATEWAY-01", [5]),
    ]
    group = group_related_alerts(alerts)[0]

    assert group.suspected_attack_path == (
        "Brute force followed by successful login -> "
        "VPN login followed by privilege escalation -> "
        "Suspicious API data download"
    )


def test_run_incident_correlation_flushes_created_links_for_summary_workflow() -> None:
    alerts = [
        alert(1, "Brute force followed by successful login", "high", "alex.morgan", "CLOUD-IAM", [1, 2, 3, 4]),
        alert(2, "Successful login from unusual IP", "medium", "alex.morgan", "CLOUD-IAM", [4]),
    ]
    session = FakeIncidentSession(alerts)

    result = run_incident_correlation(session)  # type: ignore[arg-type]

    assert result.incidents_created == 1
    assert result.incident_events_linked == 4
    assert session.flush_count == 2
    assert any(isinstance(item, IncidentEvent) for item in session.added_items)


def alert(
    alert_id: int,
    rule_name: str,
    severity: str,
    username: str,
    asset: str,
    event_ids: list[int],
    minutes: int | None = None,
) -> Alert:
    first_seen = BASE_TIME + timedelta(minutes=minutes if minutes is not None else alert_id)

    return Alert(
        id=alert_id,
        normalized_event_id=event_ids[-1],
        incident_id=None,
        alert_rule_name=rule_name,
        severity=severity,
        description=f"{rule_name} test alert",
        related_username=username,
        related_asset=asset,
        related_event_ids=event_ids,
        mitre_technique_id=None,
        first_seen=first_seen,
        last_seen=first_seen + timedelta(minutes=1),
        normalized_message=f"{rule_name} test alert",
    )


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def all(self) -> list[Any]:
        return self.items


class FakeIncidentSession:
    def __init__(self, alerts: list[Alert]) -> None:
        self.alerts = alerts
        self.added_items: list[Any] = []
        self.flush_count = 0
        self.next_id = 100

    def scalars(self, statement) -> FakeScalarResult:
        entity = statement.column_descriptions[0]["entity"]
        if entity is Alert:
            return FakeScalarResult(self.alerts)
        return FakeScalarResult([])

    def add(self, item: Any) -> None:
        self.added_items.append(item)

    def flush(self) -> None:
        self.flush_count += 1
        for item in self.added_items:
            if isinstance(item, Incident) and item.id is None:
                item.id = self.next_id
                self.next_id += 1
