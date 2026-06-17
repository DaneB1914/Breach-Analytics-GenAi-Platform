from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.etl.schemas import ExtractedRecord


@dataclass(frozen=True)
class SourceFile:
    """Configuration for one sample source file."""

    source_name: str
    file_name: str
    file_type: str


SOURCE_FILES: tuple[SourceFile, ...] = (
    SourceFile("auth", "auth_logs.json", "json"),
    SourceFile("vpn", "vpn_logs.csv", "csv"),
    SourceFile("cloud_audit", "cloud_audit_logs.json", "json"),
    SourceFile("api_access", "api_access_logs.csv", "csv"),
    SourceFile("endpoint_alert", "endpoint_alerts.json", "json"),
)


def extract_all_sources(data_dir: Path) -> list[ExtractedRecord]:
    """Read every supported source file from the data directory."""

    records: list[ExtractedRecord] = []
    for source_file in SOURCE_FILES:
        records.extend(extract_source_file(data_dir, source_file))
    return records


def extract_source_file(data_dir: Path, source_file: SourceFile) -> list[ExtractedRecord]:
    path = data_dir / source_file.file_name

    if source_file.file_type == "json":
        raw_records = read_json_records(path)
    elif source_file.file_type == "csv":
        raw_records = read_csv_records(path)
    else:
        raise ValueError(f"Unsupported file type: {source_file.file_type}")

    return [
        ExtractedRecord(
            source_name=source_file.source_name,
            source_path=path,
            raw_record=raw_record,
        )
        for raw_record in raw_records
    ]


def read_json_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return [ensure_object(record, path) for record in records]


def read_csv_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def ensure_object(record: Any, path: Path) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"Expected every record in {path} to be an object")

    return record
