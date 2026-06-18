from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas import WorkflowResponse
from app.detections.engine import run_detections
from app.etl.load import run_etl
from app.etl.run import default_data_dir
from app.incidents.engine import run_incident_correlation

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/etl", response_model=WorkflowResponse)
def run_etl_workflow(db: Session = Depends(get_db)) -> WorkflowResponse:
    data_dir = default_data_dir().resolve()

    # Workflow endpoints use a transaction so each step commits as one unit.
    with db.begin():
        result = run_etl(data_dir=data_dir, session=db)

    return WorkflowResponse(
        status="success",
        message="ETL pipeline completed",
        details={
            "data_dir": str(data_dir),
            "processed": result.processed,
            "raw_inserted": result.raw_inserted,
            "normalized_inserted": result.normalized_inserted,
            "skipped_existing": result.skipped_existing,
        },
    )


@router.post("/detections", response_model=WorkflowResponse)
def run_detection_workflow(db: Session = Depends(get_db)) -> WorkflowResponse:
    with db.begin():
        result = run_detections(db)

    return WorkflowResponse(
        status="success",
        message="Detection engine completed",
        details={
            "events_analyzed": result.events_analyzed,
            "alerts_created": result.alerts_created,
            "alerts_skipped": result.alerts_skipped,
        },
    )


@router.post("/incidents", response_model=WorkflowResponse)
def run_incident_workflow(db: Session = Depends(get_db)) -> WorkflowResponse:
    with db.begin():
        result = run_incident_correlation(db)

    return WorkflowResponse(
        status="success",
        message="Incident correlation completed",
        details={
            "alerts_analyzed": result.alerts_analyzed,
            "incidents_created": result.incidents_created,
            "alerts_linked": result.alerts_linked,
            "incident_events_linked": result.incident_events_linked,
        },
    )


@router.post("/run-all", response_model=WorkflowResponse)
def run_all_workflows(db: Session = Depends(get_db)) -> WorkflowResponse:
    data_dir = default_data_dir().resolve()

    with db.begin():
        etl_result = run_etl(data_dir=data_dir, session=db)
        detection_result = run_detections(db)
        incident_result = run_incident_correlation(db)

    return WorkflowResponse(
        status="success",
        message="ETL, detections, and incident correlation completed",
        details={
            "etl": {
                "data_dir": str(data_dir),
                "processed": etl_result.processed,
                "raw_inserted": etl_result.raw_inserted,
                "normalized_inserted": etl_result.normalized_inserted,
                "skipped_existing": etl_result.skipped_existing,
            },
            "detections": {
                "events_analyzed": detection_result.events_analyzed,
                "alerts_created": detection_result.alerts_created,
                "alerts_skipped": detection_result.alerts_skipped,
            },
            "incidents": {
                "alerts_analyzed": incident_result.alerts_analyzed,
                "incidents_created": incident_result.incidents_created,
                "alerts_linked": incident_result.alerts_linked,
                "incident_events_linked": incident_result.incident_events_linked,
            },
        },
    )
