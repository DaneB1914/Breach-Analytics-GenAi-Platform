from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.db.session import SessionLocal
from app.etl.load import run_etl


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the sample security log ETL pipeline.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="Directory containing the sample log files.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()

    # One session and one transaction keeps the ETL batch consistent.
    with SessionLocal() as session:
        with session.begin():
            result = run_etl(data_dir=data_dir, session=session)

    print(f"ETL complete for data directory: {data_dir}")
    print(f"Processed records: {result.processed}")
    print(f"Raw events inserted: {result.raw_inserted}")
    print(f"Normalized events inserted: {result.normalized_inserted}")
    print(f"Skipped existing normalized events: {result.skipped_existing}")


def default_data_dir() -> Path:
    env_data_dir = os.getenv("DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir)

    docker_data_dir = Path("/data")
    if docker_data_dir.exists():
        return docker_data_dir

    # When run from backend with `python -m app.etl.run`, data lives one level up.
    return Path.cwd().parent / "data"


if __name__ == "__main__":
    main()
