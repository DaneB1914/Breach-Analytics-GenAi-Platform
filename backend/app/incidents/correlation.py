from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.db.models import Alert, Incident
from app.incidents.schemas import IncidentGroup

CORRELATION_WINDOW = timedelta(hours=24)
SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def group_related_alerts(alerts: Iterable[Alert]) -> list[IncidentGroup]:
    """Group alerts that likely belong to the same investigation."""

    working_groups: list[list[Alert]] = []

    for alert in sort_alerts(alerts):
        for working_group in working_groups:
            if alert_belongs_to_group(alert, working_group):
                working_group.append(alert)
                break
        else:
            working_groups.append([alert])

    return [build_incident_group(group) for group in working_groups]


def alert_belongs_to_group(alert: Alert, group: list[Alert]) -> bool:
    # Main correlation logic: alerts should share a user, share an asset, or reuse
    # some of the same evidence event IDs, and they should occur close together.
    return identity_matches(alert, group) and time_window_matches(alert, group)


def identity_matches(alert: Alert, group: list[Alert]) -> bool:
    group_usernames = {value for value in (item.related_username for item in group) if value}
    group_assets = {value for value in (item.related_asset for item in group) if value}
    group_event_ids = collect_related_event_ids(group)
    alert_event_ids = collect_related_event_ids([alert])

    if group_event_ids.intersection(alert_event_ids):
        return True

    if alert.related_username or group_usernames:
        return bool(alert.related_username and alert.related_username in group_usernames)

    return bool(alert.related_asset and alert.related_asset in group_assets)


def time_window_matches(alert: Alert, group: list[Alert]) -> bool:
    group_first = first_seen(group)
    group_last = last_seen(group)
    alert_first = alert_first_seen(alert)
    alert_last = alert_last_seen(alert)

    if group_first is None or group_last is None or alert_first is None or alert_last is None:
        return True

    return alert_first <= group_last + CORRELATION_WINDOW and alert_last >= group_first - CORRELATION_WINDOW


def build_incident_group(alerts: list[Alert]) -> IncidentGroup:
    affected_user = most_common_value(alert.related_username for alert in alerts)
    affected_assets = sorted({alert.related_asset for alert in alerts if alert.related_asset})
    severity = highest_severity(alerts)
    related_event_ids = sorted(collect_related_event_ids(alerts))
    attack_path = build_suspected_attack_path(alerts)
    title = build_title(severity, affected_user, affected_assets)
    description = build_description(alerts, affected_user, affected_assets)

    return IncidentGroup(
        alerts=sort_alerts(alerts),
        title=title,
        severity=severity,
        affected_user=affected_user,
        affected_assets=affected_assets,
        related_event_ids=related_event_ids,
        suspected_attack_path=attack_path,
        description=description,
        first_seen=first_seen(alerts),
        last_seen=last_seen(alerts),
    )


def build_incident(group: IncidentGroup) -> Incident:
    return Incident(
        title=group.title,
        severity=group.severity,
        status="open",
        suspected_attack_path=group.suspected_attack_path,
        description=group.description,
        affected_user=group.affected_user,
        affected_assets=group.affected_assets,
        first_seen=group.first_seen,
        last_seen=group.last_seen,
    )


def build_title(severity: str, affected_user: str | None, affected_assets: list[str]) -> str:
    target = affected_user or ", ".join(affected_assets) or "unknown target"
    return f"{severity.title()} security incident for {target}"


def build_description(
    alerts: list[Alert],
    affected_user: str | None,
    affected_assets: list[str],
) -> str:
    user_text = affected_user or "an unknown user"
    asset_text = ", ".join(affected_assets) if affected_assets else "unknown assets"
    return f"Correlated {len(alerts)} alerts involving {user_text} and {asset_text}."


def build_suspected_attack_path(alerts: list[Alert]) -> str:
    ordered_rule_names: list[str] = []

    for alert in sort_alerts(alerts):
        if alert.alert_rule_name not in ordered_rule_names:
            ordered_rule_names.append(alert.alert_rule_name)

    return " -> ".join(ordered_rule_names)


def highest_severity(alerts: list[Alert]) -> str:
    return max((alert.severity for alert in alerts), key=severity_score)


def severity_score(severity: str | None) -> int:
    return SEVERITY_RANK.get((severity or "").lower(), 0)


def collect_related_event_ids(alerts: Iterable[Alert]) -> set[int]:
    event_ids: set[int] = set()

    for alert in alerts:
        if alert.normalized_event_id is not None:
            event_ids.add(alert.normalized_event_id)
        for event_id in alert.related_event_ids or []:
            event_ids.add(int(event_id))

    return event_ids


def first_seen(alerts: list[Alert]) -> datetime | None:
    timestamps = [alert_first_seen(alert) for alert in alerts if alert_first_seen(alert) is not None]
    return min(timestamps) if timestamps else None


def last_seen(alerts: list[Alert]) -> datetime | None:
    timestamps = [alert_last_seen(alert) for alert in alerts if alert_last_seen(alert) is not None]
    return max(timestamps) if timestamps else None


def alert_first_seen(alert: Alert) -> datetime | None:
    return alert.first_seen or alert.last_seen or alert.created_at


def alert_last_seen(alert: Alert) -> datetime | None:
    return alert.last_seen or alert.first_seen or alert.created_at


def sort_alerts(alerts: Iterable[Alert]) -> list[Alert]:
    return sorted(
        alerts,
        key=lambda alert: (
            alert_first_seen(alert) or datetime.min.replace(tzinfo=timezone.utc),
            alert.id or 0,
        ),
    )


def most_common_value(values: Iterable[str | None]) -> str | None:
    filtered_values = [value for value in values if value]
    if not filtered_values:
        return None

    return Counter(filtered_values).most_common(1)[0][0]
