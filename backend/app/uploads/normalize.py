from __future__ import annotations

from datetime import datetime
from typing import Any

from app.etl.schemas import NormalizedRecord

SOURCE_SYSTEM_DEFAULTS = {
    "auth": "CLOUD-IAM",
    "vpn": "vpn",
    "cloud": "cloud_identity",
    "api": "api_gateway",
    "endpoint": "endpoint-edr",
    "generic": "uploaded_generic",
}


def normalize_uploaded_record(record: dict[str, Any], source_type: str) -> NormalizedRecord:
    """Map common log field names into the existing NormalizedEvent schema."""

    cleaned_source_type = source_type.strip().lower() or "generic"
    action = infer_action(record)
    event_type = infer_event_type(record, cleaned_source_type, action)
    username = first_clean(record, "username", "user", "user_name", "actor", "account", "principal", "src_user")
    asset = first_clean(record, "asset", "host", "hostname", "device_name", "device", "target_resource", "resource")

    return NormalizedRecord(
        timestamp=safe_parse_timestamp(first_value(record, "timestamp", "time", "event_time", "observed_at", "datetime")),
        source_system=infer_source_system(record, cleaned_source_type),
        event_type=event_type,
        username=username,
        source_ip=first_clean(record, "source_ip", "src_ip", "client_ip", "remote_ip", "ip", "sourceAddress"),
        destination_ip=first_clean(record, "destination_ip", "dest_ip", "dst_ip", "assigned_private_ip", "server_ip"),
        asset=asset,
        action=action,
        outcome=first_clean(record, "outcome", "result", "status", "status_code", "response_code"),
        severity=lower_clean(first_value(record, "severity", "level", "risk", "priority")),
        mitre_technique_id=first_clean(record, "mitre_technique_id", "technique_id", "mitre", "technique"),
        message=infer_message(record, username, action, event_type, asset),
    )


def infer_source_system(record: dict[str, Any], source_type: str) -> str:
    explicit_source = first_clean(record, "source_system", "source", "system", "log_source", "product")
    if explicit_source:
        return explicit_source

    if source_type == "cloud":
        service = first_clean(record, "service")
        return f"cloud_{service}" if service else SOURCE_SYSTEM_DEFAULTS["cloud"]

    return SOURCE_SYSTEM_DEFAULTS.get(source_type, SOURCE_SYSTEM_DEFAULTS["generic"])


def infer_event_type(record: dict[str, Any], source_type: str, action: str | None) -> str:
    explicit_event_type = first_clean(
        record,
        "event_type",
        "type",
        "eventName",
        "event_name",
        "operation",
        "request_category",
        "alert_type",
        "category",
    )
    if explicit_event_type:
        return explicit_event_type

    if source_type == "auth":
        return "interactive_login"
    if source_type == "vpn" and action:
        return f"vpn_{action}"
    if source_type == "cloud" and action:
        return action
    if source_type == "api":
        text = " ".join(filter(None, [action, first_clean(record, "path", "url", "endpoint")])).lower()
        return "bulk_export" if "export" in text or "download" in text else "api_access"
    if source_type == "endpoint":
        return "endpoint_event"

    return "uploaded_event"


def infer_action(record: dict[str, Any]) -> str | None:
    http_method = first_clean(record, "http_method", "method")
    path = first_clean(record, "path", "url", "endpoint")
    if http_method and path:
        return f"{http_method} {path}"

    return first_clean(record, "action", "operation", "activity", "event_action")


def infer_message(
    record: dict[str, Any],
    username: str | None,
    action: str | None,
    event_type: str,
    asset: str | None,
) -> str | None:
    explicit_message = first_clean(record, "message", "reason", "description", "details", "alert")
    if explicit_message:
        return explicit_message

    parts = [
        username or "unknown user",
        action or event_type,
        f"on {asset}" if asset else None,
    ]
    return " ".join(part for part in parts if part)


def first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def first_clean(record: dict[str, Any], *keys: str) -> str | None:
    return clean(first_value(record, *keys))


def lower_clean(value: Any) -> str | None:
    text = clean(value)
    return text.lower() if text else None


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def safe_parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
