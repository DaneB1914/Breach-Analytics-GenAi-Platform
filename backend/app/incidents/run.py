from __future__ import annotations

from app.db.session import SessionLocal
from app.incidents.engine import run_incident_correlation


def main() -> None:
    # Incident correlation runs after detections, so it only looks at alerts that
    # do not already have an incident_id.
    with SessionLocal() as session:
        with session.begin():
            result = run_incident_correlation(session)

    print("Incident correlation complete")
    print(f"Unassigned alerts analyzed: {result.alerts_analyzed}")
    print(f"Incidents created: {result.incidents_created}")
    print(f"Alerts linked to incidents: {result.alerts_linked}")
    print(f"Incident event links created: {result.incident_events_linked}")


if __name__ == "__main__":
    main()
