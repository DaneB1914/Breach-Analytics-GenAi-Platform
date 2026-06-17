from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.etl.schemas import ExtractedRecord, NormalizedRecord


def normalize_extracted_record(extracted_record: ExtractedRecord) -> NormalizedRecord:
    """Route each extracted record to the right source-specific normalizer."""

    normalizers: dict[str, Callable[[dict[str, Any]], NormalizedRecord]] = {
        "auth": normalize_auth_log,
        "vpn": normalize_vpn_log,
        "cloud_audit": normalize_cloud_audit_log,
        "api_access": normalize_api_access_log,
        "endpoint_alert": normalize_endpoint_alert,
    }

    try:
        normalizer = normalizers[extracted_record.source_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported source: {extracted_record.source_name}") from exc

    return normalizer(extracted_record.raw_record)


def normalize_auth_log(record: dict[str, Any]) -> NormalizedRecord:
    return NormalizedRecord(
        timestamp=parse_timestamp(record.get("timestamp")),
        source_system=clean(record.get("source_system")) or "CLOUD-IAM",
        event_type=clean(record.get("event_type")) or "auth_event",
        username=clean(record.get("username")),
        source_ip=clean(record.get("source_ip")),
        destination_ip=None,
        asset=clean(record.get("asset")),
        action=clean(record.get("action")),
        outcome=clean(record.get("outcome")),
        severity=clean(record.get("severity")),
        mitre_technique_id=clean(record.get("mitre_technique_id")),
        message=clean(record.get("reason")),
    )


def normalize_vpn_log(record: dict[str, Any]) -> NormalizedRecord:
    action = clean(record.get("action")) or "vpn_event"
    result = clean(record.get("result"))
    session_id = clean(record.get("session_id"))

    return NormalizedRecord(
        timestamp=parse_timestamp(record.get("time")),
        source_system="vpn",
        event_type=f"vpn_{action}",
        username=clean(record.get("user")),
        source_ip=clean(record.get("client_ip")),
        destination_ip=clean(record.get("assigned_private_ip")),
        asset=clean(record.get("device_name")),
        action=action,
        outcome=result,
        severity=None,
        mitre_technique_id=None,
        message=f"VPN {action} {result or 'unknown'} for session {session_id or 'unknown'}",
    )


def normalize_cloud_audit_log(record: dict[str, Any]) -> NormalizedRecord:
    actor = clean(record.get("actor"))
    operation = clean(record.get("operation")) or "cloud_audit_event"
    target_resource = clean(record.get("target_resource"))

    return NormalizedRecord(
        timestamp=parse_timestamp(record.get("event_time")),
        source_system=f"cloud_{clean(record.get('service')) or 'audit'}",
        event_type=operation,
        username=actor,
        source_ip=clean(record.get("source_ip")),
        destination_ip=None,
        asset=clean(record.get("asset")),
        action=operation,
        outcome=clean(record.get("outcome")),
        severity=clean(record.get("severity")),
        mitre_technique_id=clean(record.get("mitre_technique_id")),
        message=f"{actor or 'unknown actor'} performed {operation} on {target_resource or 'unknown resource'}",
    )


def normalize_api_access_log(record: dict[str, Any]) -> NormalizedRecord:
    method = clean(record.get("http_method")) or "REQUEST"
    path = clean(record.get("path")) or "unknown_path"
    status_code = clean(record.get("status_code"))
    records_returned = clean(record.get("records_returned"))
    response_bytes = clean(record.get("response_bytes"))

    return NormalizedRecord(
        timestamp=parse_timestamp(record.get("timestamp")),
        source_system="api_gateway",
        event_type=clean(record.get("request_category")) or "api_access",
        username=clean(record.get("user")),
        source_ip=clean(record.get("source_ip")),
        destination_ip=None,
        asset=clean(record.get("asset")),
        action=f"{method} {path}",
        outcome=status_code,
        severity=None,
        mitre_technique_id=None,
        message=(
            f"{method} {path} returned {status_code or 'unknown'} "
            f"with {records_returned or 'unknown'} records and {response_bytes or 'unknown'} bytes"
        ),
    )


def normalize_endpoint_alert(record: dict[str, Any]) -> NormalizedRecord:
    return NormalizedRecord(
        timestamp=parse_timestamp(record.get("observed_at")),
        source_system=clean(record.get("source_system")) or "endpoint-edr",
        event_type=clean(record.get("event_type")) or "endpoint_event",
        username=clean(record.get("user_name")),
        source_ip=None,
        destination_ip=clean(record.get("destination_ip")),
        asset=clean(record.get("host")),
        action=clean(record.get("action")),
        outcome=clean(record.get("outcome")),
        severity=clean(record.get("severity")),
        mitre_technique_id=clean(record.get("mitre_technique_id")),
        message=clean(record.get("message")),
    )


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None

    # The sample files use UTC timestamps ending in Z. datetime understands +00:00.
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def clean(value: Any) -> str | None:
    """Convert blank CSV fields and JSON nulls to None."""

    if value is None:
        return None

    text = str(value).strip()
    return text or None
