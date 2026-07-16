from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.models import Incident, IncidentEvent, LLMSummary
from app.summaries.providers import get_summary_provider
from app.summaries.schemas import IncidentEvidence, SummaryDraft


def generate_and_store_summary(
    session: Session,
    incident_id: int,
    dataset_id: int | None = None,
    enforce_dataset_scope: bool = False,
) -> LLMSummary | None:
    evidence = load_incident_evidence(
        session,
        incident_id,
        dataset_id=dataset_id,
        enforce_dataset_scope=enforce_dataset_scope,
    )
    if evidence is None:
        return None

    provider = get_summary_provider(get_settings().openai_api_key)
    draft = provider.generate(evidence)
    summary = build_llm_summary(incident_id, draft)

    session.add(summary)
    session.flush()
    return summary


def load_incident_evidence(
    session: Session,
    incident_id: int,
    dataset_id: int | None = None,
    enforce_dataset_scope: bool = False,
) -> IncidentEvidence | None:
    incident = session.get(
        Incident,
        incident_id,
        options=[
            selectinload(Incident.alerts),
            selectinload(Incident.event_links).selectinload(IncidentEvent.normalized_event),
        ],
    )

    if incident is None:
        return None

    if enforce_dataset_scope and incident.dataset_id != dataset_id:
        return None

    if (
        enforce_dataset_scope
        and dataset_id is None
        and any(alert.dataset_id is not None for alert in incident.alerts)
    ):
        # Legacy mixed incidents are retained in the database but are not
        # exposed as demo investigations.
        return None

    events = [
        event_link.normalized_event
        for event_link in incident.event_links
        if event_link.normalized_event is not None
        and (
            not enforce_dataset_scope
            or event_link.normalized_event.dataset_id == dataset_id
        )
    ]
    alerts = [
        alert
        for alert in incident.alerts
        if not enforce_dataset_scope or alert.dataset_id == dataset_id
    ]
    evidence_event_ids = sorted({event.id for event in events if event.id is not None})

    return IncidentEvidence(
        incident=incident,
        alerts=alerts,
        events=events,
        evidence_event_ids=evidence_event_ids,
    )


def get_latest_summary(session: Session, incident_id: int) -> LLMSummary | None:
    return session.scalar(
        select(LLMSummary)
        .where(LLMSummary.incident_id == incident_id)
        .order_by(LLMSummary.created_at.desc(), LLMSummary.id.desc())
    )


def build_llm_summary(incident_id: int, draft: SummaryDraft) -> LLMSummary:
    return LLMSummary(
        incident_id=incident_id,
        model_name=draft.model_name,
        executive_summary=draft.executive_summary,
        technical_summary=draft.technical_summary,
        attack_timeline=draft.attack_timeline,
        affected_users=draft.affected_users,
        affected_assets=draft.affected_assets,
        suspected_attack_path=draft.suspected_attack_path,
        recommended_containment_steps=draft.recommended_containment_steps,
        evidence_event_ids=draft.evidence_event_ids,
    )
