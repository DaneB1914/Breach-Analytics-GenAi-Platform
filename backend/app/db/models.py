from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawEvent(Base):
    """Original security event exactly as it was ingested."""

    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_system: Mapped[str] = mapped_column(String(100), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    normalized_events: Mapped[list[NormalizedEvent]] = relationship(
        back_populates="raw_event",
        cascade="all, delete-orphan",
    )


class NormalizedEvent(Base):
    """Clean, consistent version of a raw event after ETL normalization."""

    __tablename__ = "normalized_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_event_id: Mapped[int] = mapped_column(
        ForeignKey("raw_events.id", ondelete="CASCADE"),
        index=True,
    )
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_system: Mapped[str] = mapped_column(String(100), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    username: Mapped[str | None] = mapped_column(String(255), index=True)
    source_ip: Mapped[str | None] = mapped_column(String(45), index=True)
    destination_ip: Mapped[str | None] = mapped_column(String(45))
    asset: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str | None] = mapped_column(String(100))
    outcome: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str | None] = mapped_column(String(50))
    mitre_technique_id: Mapped[str | None] = mapped_column(String(50))
    normalized_message: Mapped[str | None] = mapped_column(Text)

    raw_event: Mapped[RawEvent] = relationship(back_populates="normalized_events")
    alerts: Mapped[list[Alert]] = relationship(back_populates="normalized_event")
    incident_links: Mapped[list[IncidentEvent]] = relationship(
        back_populates="normalized_event",
        cascade="all, delete-orphan",
    )


class Alert(Base):
    """Suspicious activity produced by a future detection rule."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    normalized_event_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_events.id", ondelete="CASCADE"),
        index=True,
    )
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    alert_rule_name: Mapped[str] = mapped_column(String(200), index=True)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    mitre_technique_id: Mapped[str | None] = mapped_column(String(50))
    normalized_message: Mapped[str] = mapped_column(Text)

    normalized_event: Mapped[NormalizedEvent] = relationship(back_populates="alerts")
    incident: Mapped[Incident | None] = relationship(back_populates="alerts")


class Incident(Base):
    """Group of related alerts and events that represent one investigation."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), server_default=text("'open'"), index=True)
    severity: Mapped[str | None] = mapped_column(String(50))
    affected_user: Mapped[str | None] = mapped_column(String(255), index=True)
    affected_assets: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    alerts: Mapped[list[Alert]] = relationship(back_populates="incident")
    event_links: Mapped[list[IncidentEvent]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    llm_summaries: Mapped[list[LLMSummary]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class IncidentEvent(Base):
    """Association table connecting incidents to the events used as evidence."""

    __tablename__ = "incident_events"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "normalized_event_id",
            name="uq_incident_events_incident_normalized_event",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    normalized_event_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_events.id", ondelete="CASCADE"),
        index=True,
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    incident: Mapped[Incident] = relationship(back_populates="event_links")
    normalized_event: Mapped[NormalizedEvent] = relationship(back_populates="incident_links")


class LLMSummary(Base):
    """Auditable AI-generated summary for a future incident workflow."""

    __tablename__ = "llm_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    model_name: Mapped[str | None] = mapped_column(String(100))
    executive_summary: Mapped[str] = mapped_column(Text)
    technical_summary: Mapped[str] = mapped_column(Text)
    evidence_event_ids: Mapped[list[int]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    incident: Mapped[Incident] = relationship(back_populates="llm_summaries")
