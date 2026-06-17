from pathlib import Path

from app.etl.extract import extract_all_sources, read_csv_records, read_json_records
from app.etl.normalize import (
    normalize_api_access_log,
    normalize_auth_log,
    normalize_cloud_audit_log,
    normalize_endpoint_alert,
    normalize_extracted_record,
    normalize_vpn_log,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def test_auth_log_normalization() -> None:
    record = find_json_record("auth_logs.json", "event_id", "auth-1008")

    normalized = normalize_auth_log(record)

    assert normalized.source_system == "CLOUD-IAM"
    assert normalized.event_type == "interactive_login"
    assert normalized.username == "alex.morgan"
    assert normalized.source_ip == "203.0.113.77"
    assert normalized.asset == "CLOUD-IAM"
    assert normalized.action == "login"
    assert normalized.outcome == "success"
    assert normalized.message == "successful login after repeated failures"


def test_vpn_log_normalization() -> None:
    record = find_csv_record("vpn_logs.csv", "vpn_event_id", "vpn-2003")

    normalized = normalize_vpn_log(record)

    assert normalized.source_system == "vpn"
    assert normalized.event_type == "vpn_connect"
    assert normalized.username == "alex.morgan"
    assert normalized.source_ip == "203.0.113.77"
    assert normalized.destination_ip == "10.8.14.23"
    assert normalized.asset == "LAPTOP-ALEX-01"
    assert normalized.action == "connect"
    assert normalized.outcome == "success"
    assert normalized.message == "VPN connect success for session vpn-alex-7731"


def test_cloud_audit_log_normalization() -> None:
    record = find_json_record("cloud_audit_logs.json", "audit_id", "audit-3005")

    normalized = normalize_cloud_audit_log(record)

    assert normalized.source_system == "cloud_identity"
    assert normalized.event_type == "AttachUserPolicy"
    assert normalized.username == "alex.morgan"
    assert normalized.source_ip == "203.0.113.77"
    assert normalized.asset == "CLOUD-IAM"
    assert normalized.action == "AttachUserPolicy"
    assert normalized.outcome == "success"
    assert normalized.message == "alex.morgan performed AttachUserPolicy on alex.morgan"


def test_api_access_log_normalization() -> None:
    record = find_csv_record("api_access_logs.csv", "request_id", "req-4005")

    normalized = normalize_api_access_log(record)

    assert normalized.source_system == "api_gateway"
    assert normalized.event_type == "bulk_export"
    assert normalized.username == "alex.morgan"
    assert normalized.source_ip == "10.8.14.23"
    assert normalized.asset == "API-GATEWAY-01"
    assert normalized.action == "GET /api/v1/customers/export?region=all"
    assert normalized.outcome == "200"
    assert normalized.message == (
        "GET /api/v1/customers/export?region=all returned 200 "
        "with 48320 records and 93218422 bytes"
    )


def test_endpoint_alert_normalization() -> None:
    record = find_json_record("endpoint_alerts.json", "endpoint_event_id", "end-5004")

    normalized = normalize_endpoint_alert(record)

    assert normalized.source_system == "endpoint-edr"
    assert normalized.event_type == "credential_access"
    assert normalized.username == "alex.morgan"
    assert normalized.destination_ip is None
    assert normalized.asset == "LAPTOP-ALEX-01"
    assert normalized.action == "block"
    assert normalized.outcome == "prevented"
    assert normalized.severity == "high"
    assert normalized.mitre_technique_id == "T1003.001"


def test_all_sample_files_extract_and_normalize_without_crashing() -> None:
    extracted_records = extract_all_sources(DATA_DIR)

    normalized_records = [
        normalize_extracted_record(extracted_record)
        for extracted_record in extracted_records
    ]

    assert len(extracted_records) == 49
    assert len(normalized_records) == 49
    assert {record.source_name for record in extracted_records} == {
        "auth",
        "vpn",
        "cloud_audit",
        "api_access",
        "endpoint_alert",
    }


def find_json_record(file_name: str, key: str, value: str) -> dict:
    return find_record(read_json_records(DATA_DIR / file_name), key, value)


def find_csv_record(file_name: str, key: str, value: str) -> dict:
    return find_record(read_csv_records(DATA_DIR / file_name), key, value)


def find_record(records: list[dict], key: str, value: str) -> dict:
    for record in records:
        if record.get(key) == value:
            return record

    raise AssertionError(f"Could not find record where {key}={value}")
