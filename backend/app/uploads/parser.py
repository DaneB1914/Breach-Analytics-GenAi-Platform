from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

ALLOWED_SOURCE_TYPES = {"auth", "vpn", "cloud", "api", "endpoint", "generic"}
SUPPORTED_EXTENSIONS = {".csv", ".json", ".ndjson"}


class UploadParseError(ValueError):
    """Raised when an uploaded file cannot be parsed into event records."""


def validate_source_type(source_type: str) -> str:
    cleaned = source_type.strip().lower()
    if cleaned not in ALLOWED_SOURCE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
        raise UploadParseError(f"Unsupported source_type '{source_type}'. Use one of: {allowed}.")
    return cleaned


def parse_upload_records(filename: str, content: bytes) -> list[dict[str, Any]]:
    """Parse CSV, JSON arrays, JSON objects, or newline-delimited JSON records."""

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UploadParseError("Only .csv, .json, and .ndjson uploads are supported.")

    text = content.decode("utf-8-sig").strip()
    if not text:
        return []

    if suffix == ".csv":
        return parse_csv_records(text)

    return parse_json_records(text)


def parse_csv_records(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(StringIO(text))
    return [dict(row) for row in reader]


def parse_json_records(text: str) -> list[dict[str, Any]]:
    if text.startswith("[") or text.startswith("{"):
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise UploadParseError("JSON uploads must contain an object or an array of objects.")
        return ensure_record_objects(parsed)

    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return ensure_record_objects(records)


def ensure_record_objects(records: list[Any]) -> list[dict[str, Any]]:
    cleaned_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise UploadParseError("Each uploaded record must be a JSON object or CSV row.")
        cleaned_records.append(record)
    return cleaned_records
