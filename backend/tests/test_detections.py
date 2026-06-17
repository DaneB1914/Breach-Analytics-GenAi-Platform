from datetime import datetime, timedelta, timezone

from app.db.models import NormalizedEvent
from app.detections.rules import (
    API_DOWNLOAD_RULE,
    BRUTE_FORCE_RULE,
    ENDPOINT_CREDENTIAL_RULE,
    MULTIPLE_HIGH_RULE,
    UNUSUAL_IP_RULE,
    VPN_PRIVILEGE_RULE,
    detect_brute_force_followed_by_success,
    detect_endpoint_malware_or_credential_access,
    detect_multiple_high_severity_events,
    detect_successful_login_from_unusual_ip,
    detect_suspicious_api_download,
    detect_vpn_followed_by_privilege_escalation,
)

BASE_TIME = datetime(2026, 6, 16, 8, 42, tzinfo=timezone.utc)


def test_detects_brute_force_followed_by_success() -> None:
    events = [
        event(1, minutes=0, outcome="failure"),
        event(2, minutes=1, outcome="failure"),
        event(3, minutes=2, outcome="failure"),
        event(4, minutes=4, outcome="success"),
    ]

    alerts = detect_brute_force_followed_by_success(events)

    assert len(alerts) == 1
    assert alerts[0].rule_name == BRUTE_FORCE_RULE
    assert alerts[0].severity == "high"
    assert alerts[0].related_username == "alex.morgan"
    assert alerts[0].related_event_ids == [1, 2, 3, 4]
    assert alerts[0].mitre_technique_id == "T1110"


def test_detects_successful_login_from_unusual_ip() -> None:
    events = [
        event(1, username="jamie.lee", source_ip="198.51.100.24", outcome="success"),
        event(2, username="alex.morgan", source_ip="203.0.113.77", outcome="success"),
    ]

    alerts = detect_successful_login_from_unusual_ip(events)

    assert len(alerts) == 1
    assert alerts[0].rule_name == UNUSUAL_IP_RULE
    assert alerts[0].severity == "medium"
    assert alerts[0].related_username == "alex.morgan"
    assert alerts[0].related_event_ids == [2]
    assert alerts[0].mitre_technique_id == "T1078"


def test_detects_vpn_followed_by_privilege_escalation() -> None:
    events = [
        vpn_event(1, minutes=10),
        cloud_event(2, minutes=20, action="CreateAccessKey"),
        cloud_event(3, minutes=25, action="AttachUserPolicy"),
    ]

    alerts = detect_vpn_followed_by_privilege_escalation(events)

    assert len(alerts) == 1
    assert alerts[0].rule_name == VPN_PRIVILEGE_RULE
    assert alerts[0].severity == "high"
    assert alerts[0].related_username == "alex.morgan"
    assert alerts[0].related_asset == "CLOUD-IAM"
    assert alerts[0].related_event_ids == [1, 2, 3]
    assert alerts[0].mitre_technique_id == "T1098"


def test_detects_suspicious_api_download() -> None:
    events = [
        api_event(1, event_type="normal_report", records_action="GET /api/v1/reports/weekly"),
        api_event(2, event_type="bulk_export", records_action="GET /api/v1/customers/export?region=all"),
    ]

    alerts = detect_suspicious_api_download(events)

    assert len(alerts) == 1
    assert alerts[0].rule_name == API_DOWNLOAD_RULE
    assert alerts[0].severity == "high"
    assert alerts[0].related_asset == "API-GATEWAY-01"
    assert alerts[0].related_event_ids == [2]
    assert alerts[0].mitre_technique_id == "T1530"


def test_detects_endpoint_malware_or_credential_access() -> None:
    events = [
        endpoint_event(1, event_type="process_start", severity="low", mitre_technique_id=None),
        endpoint_event(2, event_type="credential_access", severity="high", mitre_technique_id="T1003.001"),
    ]

    alerts = detect_endpoint_malware_or_credential_access(events)

    assert len(alerts) == 1
    assert alerts[0].rule_name == ENDPOINT_CREDENTIAL_RULE
    assert alerts[0].severity == "high"
    assert alerts[0].related_asset == "LAPTOP-ALEX-01"
    assert alerts[0].related_event_ids == [2]
    assert alerts[0].mitre_technique_id == "T1003.001"


def test_detects_multiple_high_severity_events_by_same_user() -> None:
    events = [
        endpoint_event(1, minutes=0, event_type="remote_file_download", severity="high"),
        endpoint_event(2, minutes=5, event_type="archive_created", severity="high"),
        endpoint_event(3, minutes=10, event_type="network_connection", severity="critical"),
        endpoint_event(4, minutes=11, username="jamie.lee", event_type="endpoint_scan", severity="low"),
    ]

    alerts = detect_multiple_high_severity_events(events)

    assert len(alerts) == 1
    assert alerts[0].rule_name == MULTIPLE_HIGH_RULE
    assert alerts[0].severity == "critical"
    assert alerts[0].related_username == "alex.morgan"
    assert alerts[0].related_event_ids == [1, 2, 3]


def event(
    event_id: int,
    minutes: int = 0,
    username: str = "alex.morgan",
    source_ip: str = "203.0.113.77",
    outcome: str = "success",
) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        raw_event_id=event_id,
        event_timestamp=BASE_TIME + timedelta(minutes=minutes),
        source_system="CLOUD-IAM",
        event_type="interactive_login",
        username=username,
        source_ip=source_ip,
        destination_ip=None,
        asset="CLOUD-IAM",
        action="login",
        outcome=outcome,
        severity=None,
        mitre_technique_id=None,
        normalized_message="test auth event",
    )


def vpn_event(event_id: int, minutes: int) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        raw_event_id=event_id,
        event_timestamp=BASE_TIME + timedelta(minutes=minutes),
        source_system="vpn",
        event_type="vpn_connect",
        username="alex.morgan",
        source_ip="203.0.113.77",
        destination_ip="10.8.14.23",
        asset="LAPTOP-ALEX-01",
        action="connect",
        outcome="success",
        severity=None,
        mitre_technique_id=None,
        normalized_message="VPN connect success",
    )


def cloud_event(event_id: int, minutes: int, action: str) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        raw_event_id=event_id,
        event_timestamp=BASE_TIME + timedelta(minutes=minutes),
        source_system="cloud_identity",
        event_type=action,
        username="alex.morgan",
        source_ip="203.0.113.77",
        destination_ip=None,
        asset="CLOUD-IAM",
        action=action,
        outcome="success",
        severity=None,
        mitre_technique_id=None,
        normalized_message=f"alex.morgan performed {action}",
    )


def api_event(event_id: int, event_type: str, records_action: str) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        raw_event_id=event_id,
        event_timestamp=BASE_TIME + timedelta(minutes=30),
        source_system="api_gateway",
        event_type=event_type,
        username="alex.morgan",
        source_ip="10.8.14.23",
        destination_ip=None,
        asset="API-GATEWAY-01",
        action=records_action,
        outcome="200",
        severity=None,
        mitre_technique_id=None,
        normalized_message="API test event",
    )


def endpoint_event(
    event_id: int,
    minutes: int = 0,
    username: str = "alex.morgan",
    event_type: str = "credential_access",
    severity: str = "high",
    mitre_technique_id: str | None = "T1003.001",
) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        raw_event_id=event_id,
        event_timestamp=BASE_TIME + timedelta(minutes=minutes),
        source_system="endpoint-edr",
        event_type=event_type,
        username=username,
        source_ip=None,
        destination_ip=None,
        asset="LAPTOP-ALEX-01",
        action="alert",
        outcome="observed",
        severity=severity,
        mitre_technique_id=mitre_technique_id,
        normalized_message="Endpoint test event",
    )
