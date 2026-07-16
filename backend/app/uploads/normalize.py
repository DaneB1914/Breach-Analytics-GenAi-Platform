from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from app.etl.schemas import NormalizedRecord

SOURCE_SYSTEM_DEFAULTS = {
    "auth": "CLOUD-IAM",
    "vpn": "vpn",
    "cloud": "cloud_identity",
    "api": "api_gateway",
    "endpoint": "endpoint-edr",
    "generic": "uploaded_generic",
}


@dataclass(frozen=True)
class FieldMappingRule:
    source_field: str
    transformation_type: str = "direct"
    default_value: str | None = None


def normalize_uploaded_record(
    record: dict[str, Any],
    source_type: str,
    field_mappings: Mapping[str, FieldMappingRule] | None = None,
) -> NormalizedRecord:
    """Apply confirmed mappings first, then keep safe automatic fallbacks."""

    automatic = normalize_automatically(record, source_type)
    if not field_mappings:
        return automatic

    cleaned_source_type = source_type.strip().lower() or "generic"

    return NormalizedRecord(
        timestamp=mapped_timestamp(record, field_mappings.get("timestamp"), automatic.timestamp),
        source_system=mapped_text(
            record,
            field_mappings.get("source_system"),
            automatic.source_system,
        )
        or SOURCE_SYSTEM_DEFAULTS.get(cleaned_source_type, SOURCE_SYSTEM_DEFAULTS["generic"]),
        event_type=mapped_text(
            record,
            field_mappings.get("event_type"),
            automatic.event_type,
        )
        or "uploaded_event",
        username=mapped_text(record, field_mappings.get("username"), automatic.username),
        source_ip=mapped_text(record, field_mappings.get("source_ip"), automatic.source_ip),
        destination_ip=mapped_text(
            record,
            field_mappings.get("destination_ip"),
            automatic.destination_ip,
        ),
        asset=mapped_text(record, field_mappings.get("asset"), automatic.asset),
        action=mapped_text(record, field_mappings.get("action"), automatic.action),
        outcome=mapped_text(record, field_mappings.get("outcome"), automatic.outcome),
        severity=mapped_lower_text(record, field_mappings.get("severity"), automatic.severity),
        mitre_technique_id=mapped_text(
            record,
            field_mappings.get("mitre_technique_id"),
            automatic.mitre_technique_id,
        ),
        message=mapped_text(record, field_mappings.get("message"), automatic.message),
    )


def normalize_automatically(record: dict[str, Any], source_type: str) -> NormalizedRecord:
    """Map recognized aliases into the normalized event schema."""

    cleaned_source_type = source_type.strip().lower() or "generic"
    action = infer_action(record)
    event_type = infer_event_type(record, cleaned_source_type, action)
    username = first_clean(record, "username", "user", "user_name", "actor", "account", "principal", "src_user")
    asset = first_clean(record, "asset", "host", "hostname", "device_name", "device", "target_resource", "resource")

    return NormalizedRecord(
        timestamp=safe_parse_timestamp(
            first_value(
                record,
                "timestamp",
                "time",
                "event_time",
                "eventTime",
                "activityDateTime",
                "published",
                "createdDateTime",
                "observed_at",
                "datetime",
            )
        ),
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
        value = get_dotted_value(record, key)
        if value not in (None, ""):
            return value
    return None


def get_dotted_value(record: dict[str, Any], path: str) -> Any:
    if path in record:
        return record[path]

    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def mapped_timestamp(
    record: dict[str, Any],
    rule: FieldMappingRule | None,
    automatic_value: datetime | None,
) -> datetime | None:
    if rule is None:
        return automatic_value
    return safe_parse_timestamp(mapped_value(record, rule))


def mapped_text(
    record: dict[str, Any],
    rule: FieldMappingRule | None,
    automatic_value: str | None,
) -> str | None:
    if rule is None:
        return automatic_value
    return clean(mapped_value(record, rule))


def mapped_lower_text(
    record: dict[str, Any],
    rule: FieldMappingRule | None,
    automatic_value: str | None,
) -> str | None:
    value = mapped_text(record, rule, automatic_value)
    return value.lower() if value else None


def mapped_value(record: dict[str, Any], rule: FieldMappingRule) -> Any:
    value = get_dotted_value(record, rule.source_field)
    if value in (None, ""):
        value = rule.default_value

    if value is None:
        return None
    if rule.transformation_type == "lowercase":
        return str(value).lower()
    if rule.transformation_type == "uppercase":
        return str(value).upper()
    return value


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
