from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExtractedRecord:
    """A single source record read from a JSON or CSV log file."""

    source_name: str
    source_path: Path
    raw_record: dict[str, Any]


@dataclass(frozen=True)
class NormalizedRecord:
    """Common event shape used before loading into NormalizedEvent."""

    timestamp: datetime | None
    source_system: str
    event_type: str
    username: str | None
    source_ip: str | None
    destination_ip: str | None
    asset: str | None
    action: str | None
    outcome: str | None
    severity: str | None
    mitre_technique_id: str | None
    message: str | None


@dataclass(frozen=True)
class ETLResult:
    """Summary of one ETL run."""

    processed: int
    raw_inserted: int
    normalized_inserted: int
    skipped_existing: int
