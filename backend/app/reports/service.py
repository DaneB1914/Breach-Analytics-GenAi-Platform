from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.reports.markdown import render_markdown_report
from app.summaries.service import get_latest_summary, load_incident_evidence


def generate_incident_markdown_report(
    session: Session,
    incident_id: int,
    generated_at: datetime | None = None,
    dataset_id: int | None = None,
    enforce_dataset_scope: bool = False,
) -> str | None:
    """Load incident evidence and return a Markdown report."""

    evidence = load_incident_evidence(
        session,
        incident_id,
        dataset_id=dataset_id,
        enforce_dataset_scope=enforce_dataset_scope,
    )
    if evidence is None:
        return None

    summary = get_latest_summary(session, incident_id)
    return render_markdown_report(evidence, summary, generated_at)
