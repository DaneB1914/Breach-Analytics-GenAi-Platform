from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.db.models import NormalizedEvent
from app.detections.schemas import AlertCandidate

BRUTE_FORCE_RULE = "Brute force followed by successful login"
UNUSUAL_IP_RULE = "Successful login from unusual IP"
VPN_PRIVILEGE_RULE = "VPN login followed by privilege escalation"
API_DOWNLOAD_RULE = "Suspicious API data download"
ENDPOINT_CREDENTIAL_RULE = "Endpoint malware or credential access"
MULTIPLE_HIGH_RULE = "Multiple high-severity events by same user within 24 hours"

NORMAL_LOGIN_IPS = {"198.51.100.24", "10.20.5.15"}
PRIVILEGE_ACTIONS = {"AttachUserPolicy", "CreateAccessKey", "DisableMFADevice", "UpdateSecurityGroup"}
SUSPICIOUS_API_EVENT_TYPES = {"bulk_export", "file_archive_download"}
HIGH_SEVERITIES = {"high", "critical"}


def collect_alert_candidates(events: Iterable[NormalizedEvent]) -> list[AlertCandidate]:
    event_list = sort_events(events)
    candidates: list[AlertCandidate] = []

    candidates.extend(detect_brute_force_followed_by_success(event_list))
    candidates.extend(detect_successful_login_from_unusual_ip(event_list))
    candidates.extend(detect_vpn_followed_by_privilege_escalation(event_list))
    candidates.extend(detect_suspicious_api_download(event_list))
    candidates.extend(detect_endpoint_malware_or_credential_access(event_list))
    candidates.extend(detect_multiple_high_severity_events(event_list))

    return candidates


def detect_brute_force_followed_by_success(events: list[NormalizedEvent]) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []

    for event in events:
        if not is_successful_login(event) or event.event_timestamp is None:
            continue

        window_start = event.event_timestamp - timedelta(minutes=15)
        failures = [
            previous_event
            for previous_event in events
            if is_failed_login(previous_event)
            and previous_event.username == event.username
            and previous_event.source_ip == event.source_ip
            and previous_event.event_timestamp is not None
            and window_start <= previous_event.event_timestamp <= event.event_timestamp
        ]

        # This rule looks for password spraying or repeated guesses that later work.
        if len(failures) < 3:
            continue

        related_events = failures + [event]
        candidates.append(
            build_candidate(
                rule_name=BRUTE_FORCE_RULE,
                severity="high",
                description=(
                    f"{event.username} had {len(failures)} failed logins followed by a "
                    f"successful login from {event.source_ip}."
                ),
                related_username=event.username,
                related_asset=event.asset,
                related_events=related_events,
                primary_event=event,
                mitre_technique_id="T1110",
            )
        )

    return candidates


def detect_successful_login_from_unusual_ip(events: list[NormalizedEvent]) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []

    for event in events:
        # In this training dataset, 203.0.113.x is the unusual external network.
        if not is_successful_login(event):
            continue
        if event.source_ip in NORMAL_LOGIN_IPS or not event.source_ip:
            continue

        candidates.append(
            build_candidate(
                rule_name=UNUSUAL_IP_RULE,
                severity="medium",
                description=f"{event.username} successfully logged in from unusual IP {event.source_ip}.",
                related_username=event.username,
                related_asset=event.asset,
                related_events=[event],
                primary_event=event,
                mitre_technique_id="T1078",
            )
        )

    return candidates


def detect_vpn_followed_by_privilege_escalation(events: list[NormalizedEvent]) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []
    vpn_events = [event for event in events if is_successful_vpn_login(event)]

    for vpn_event in vpn_events:
        if vpn_event.event_timestamp is None or not vpn_event.username:
            continue

        window_end = vpn_event.event_timestamp + timedelta(hours=1)
        privilege_events = [
            event
            for event in events
            if is_privilege_escalation(event)
            and event.username == vpn_event.username
            and event.event_timestamp is not None
            and vpn_event.event_timestamp <= event.event_timestamp <= window_end
        ]

        # This rule links remote access to later admin or account-control changes.
        if not privilege_events:
            continue

        related_events = [vpn_event] + privilege_events
        last_privilege_event = privilege_events[-1]
        candidates.append(
            build_candidate(
                rule_name=VPN_PRIVILEGE_RULE,
                severity="high",
                description=(
                    f"{vpn_event.username} connected to VPN and then performed "
                    f"{len(privilege_events)} privilege-sensitive cloud actions."
                ),
                related_username=vpn_event.username,
                related_asset=last_privilege_event.asset or vpn_event.asset,
                related_events=related_events,
                primary_event=last_privilege_event,
                mitre_technique_id="T1098",
            )
        )

    return candidates


def detect_suspicious_api_download(events: list[NormalizedEvent]) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []

    for event in events:
        # Bulk exports and archive downloads are not always malicious, but they are
        # worth alerting on when they appear in this suspicious timeline.
        if event.source_system != "api_gateway":
            continue
        if event.event_type not in SUSPICIOUS_API_EVENT_TYPES:
            continue
        if event.outcome != "200":
            continue

        candidates.append(
            build_candidate(
                rule_name=API_DOWNLOAD_RULE,
                severity="high",
                description=f"{event.username} performed suspicious API download: {event.action}.",
                related_username=event.username,
                related_asset=event.asset,
                related_events=[event],
                primary_event=event,
                mitre_technique_id="T1530",
            )
        )

    return candidates


def detect_endpoint_malware_or_credential_access(events: list[NormalizedEvent]) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []

    for event in events:
        # Endpoint detections with credential-access techniques should become alerts
        # even when the endpoint tool reports that the action was blocked.
        if event.source_system != "endpoint-edr":
            continue
        if not is_endpoint_credential_or_malware_event(event):
            continue

        candidates.append(
            build_candidate(
                rule_name=ENDPOINT_CREDENTIAL_RULE,
                severity=event.severity or "high",
                description=event.normalized_message or "Endpoint malware or credential access activity observed.",
                related_username=event.username,
                related_asset=event.asset,
                related_events=[event],
                primary_event=event,
                mitre_technique_id=event.mitre_technique_id,
            )
        )

    return candidates


def detect_multiple_high_severity_events(events: list[NormalizedEvent]) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []
    events_by_user: dict[str, list[NormalizedEvent]] = defaultdict(list)

    for event in events:
        if event.username and severity_value(event.severity) in HIGH_SEVERITIES:
            events_by_user[event.username].append(event)

    for username, user_events in events_by_user.items():
        sorted_user_events = sort_events(user_events)

        for start_index, first_event in enumerate(sorted_user_events):
            if first_event.event_timestamp is None:
                continue

            window_end = first_event.event_timestamp + timedelta(hours=24)
            window_events = [
                event
                for event in sorted_user_events[start_index:]
                if event.event_timestamp is not None and event.event_timestamp <= window_end
            ]

            # This rule catches repeated serious endpoint or security events for
            # one user before incident correlation exists.
            if len(window_events) < 3:
                continue

            primary_event = window_events[-1]
            candidates.append(
                build_candidate(
                    rule_name=MULTIPLE_HIGH_RULE,
                    severity="critical",
                    description=(
                        f"{username} generated {len(window_events)} high or critical "
                        "events within 24 hours."
                    ),
                    related_username=username,
                    related_asset=primary_event.asset,
                    related_events=window_events,
                    primary_event=primary_event,
                    mitre_technique_id=None,
                )
            )
            break

    return candidates


def build_candidate(
    rule_name: str,
    severity: str,
    description: str,
    related_username: str | None,
    related_asset: str | None,
    related_events: list[NormalizedEvent],
    primary_event: NormalizedEvent,
    mitre_technique_id: str | None,
) -> AlertCandidate:
    event_ids = [event.id for event in related_events if event.id is not None]

    if primary_event.id is None:
        raise ValueError("Detection candidates require persisted NormalizedEvent IDs")

    return AlertCandidate(
        rule_name=rule_name,
        severity=severity,
        description=description,
        related_username=related_username,
        related_asset=related_asset,
        related_event_ids=event_ids,
        primary_event_id=primary_event.id,
        mitre_technique_id=mitre_technique_id,
        first_seen=first_seen(related_events),
        last_seen=last_seen(related_events),
    )


def is_successful_login(event: NormalizedEvent) -> bool:
    return (
        event.source_system == "CLOUD-IAM"
        and event.event_type == "interactive_login"
        and event.action == "login"
        and event.outcome == "success"
    )


def is_failed_login(event: NormalizedEvent) -> bool:
    return (
        event.source_system == "CLOUD-IAM"
        and event.event_type == "interactive_login"
        and event.action == "login"
        and event.outcome == "failure"
    )


def is_successful_vpn_login(event: NormalizedEvent) -> bool:
    return event.source_system == "vpn" and event.action == "connect" and event.outcome == "success"


def is_privilege_escalation(event: NormalizedEvent) -> bool:
    return event.source_system == "cloud_identity" and event.action in PRIVILEGE_ACTIONS


def is_endpoint_credential_or_malware_event(event: NormalizedEvent) -> bool:
    event_type = event.event_type or ""
    message = (event.normalized_message or "").lower()

    return (
        event_type in {"credential_access", "malware_detected"}
        or event.mitre_technique_id == "T1003.001"
        or "credential" in message
        or "malware" in message
    )


def severity_value(severity: str | None) -> str | None:
    return severity.lower() if severity else None


def sort_events(events: Iterable[NormalizedEvent]) -> list[NormalizedEvent]:
    return sorted(
        events,
        key=lambda event: (
            event.event_timestamp or datetime.min.replace(tzinfo=timezone.utc),
            event.id or 0,
        ),
    )


def first_seen(events: list[NormalizedEvent]) -> datetime | None:
    timestamps = [event.event_timestamp for event in events if event.event_timestamp is not None]
    return min(timestamps) if timestamps else None


def last_seen(events: list[NormalizedEvent]) -> datetime | None:
    timestamps = [event.event_timestamp for event in events if event.event_timestamp is not None]
    return max(timestamps) if timestamps else None
