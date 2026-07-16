from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas import AlertResponse
from app.db.models import Alert

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    severity: str | None = None,
    related_username: str | None = None,
    alert_rule_name: str | None = None,
    incident_id: int | None = None,
) -> list[Alert]:
    # Uploaded alerts are available only through their dataset-scoped routes.
    statement = select(Alert).where(Alert.dataset_id.is_(None))
    statement = apply_alert_filters(
        statement=statement,
        severity=severity,
        related_username=related_username,
        alert_rule_name=alert_rule_name,
        incident_id=incident_id,
    )
    statement = statement.order_by(Alert.first_seen.desc(), Alert.id.desc()).offset(skip).limit(limit)

    return list(db.scalars(statement).all())


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.scalar(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.dataset_id.is_(None),
        )
    )

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


def apply_alert_filters(
    statement: Select[tuple[Alert]],
    severity: str | None,
    related_username: str | None,
    alert_rule_name: str | None,
    incident_id: int | None,
) -> Select[tuple[Alert]]:
    if severity:
        statement = statement.where(Alert.severity == severity)
    if related_username:
        statement = statement.where(Alert.related_username == related_username)
    if alert_rule_name:
        statement = statement.where(Alert.alert_rule_name == alert_rule_name)
    if incident_id is not None:
        statement = statement.where(Alert.incident_id == incident_id)

    return statement
