from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_event_id: int
    normalized_at: datetime | None = None
    event_timestamp: datetime | None = None
    source_system: str
    event_type: str
    username: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    asset: str | None = None
    action: str | None = None
    outcome: str | None = None
    severity: str | None = None
    mitre_technique_id: str | None = None
    normalized_message: str | None = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    normalized_event_id: int
    incident_id: int | None = None
    created_at: datetime | None = None
    alert_rule_name: str
    severity: str
    description: str
    related_username: str | None = None
    related_asset: str | None = None
    related_event_ids: list[int]
    mitre_technique_id: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    normalized_message: str


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    status: str
    severity: str | None = None
    title: str
    suspected_attack_path: str | None = None
    description: str | None = None
    affected_user: str | None = None
    affected_assets: list[str]
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class IncidentDetailResponse(IncidentResponse):
    alerts: list[AlertResponse]
    related_events: list[EventResponse]


class LLMSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    created_at: datetime | None = None
    model_name: str | None = None
    executive_summary: str
    technical_summary: str
    attack_timeline: list[dict[str, Any]]
    affected_users: list[str]
    affected_assets: list[str]
    suspected_attack_path: str | None = None
    recommended_containment_steps: list[str]
    evidence_event_ids: list[int]


class WorkflowResponse(BaseModel):
    status: str
    message: str
    details: dict[str, Any]
