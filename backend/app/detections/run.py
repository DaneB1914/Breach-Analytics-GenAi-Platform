from __future__ import annotations

from app.db.session import SessionLocal
from app.detections.engine import run_detections


def main() -> None:
    # One transaction keeps the alert batch consistent.
    with SessionLocal() as session:
        with session.begin():
            result = run_detections(session)

    print("Detection run complete")
    print(f"Normalized events analyzed: {result.events_analyzed}")
    print(f"Alerts created: {result.alerts_created}")
    print(f"Duplicate alerts skipped: {result.alerts_skipped}")


if __name__ == "__main__":
    main()
