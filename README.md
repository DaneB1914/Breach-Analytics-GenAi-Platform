# Breach Analytics GenAI Platform

A portfolio project for a breach analytics AI/GenAI contractor role. The planned platform will ingest fake security logs, normalize them through ETL, store them in PostgreSQL, detect suspicious activity, group alerts into incidents, and optionally generate auditable incident summaries with an LLM.

## Current Phase: ETL Pipeline

This project currently includes:

- FastAPI application package
- `GET /health` endpoint
- Backend Python dependencies
- A pytest smoke test for the health endpoint
- Docker Compose support
- PostgreSQL service named `db`
- Backend service named `backend`
- Environment-based `DATABASE_URL` configuration
- SQLAlchemy database models for breach analytics entities
- Alembic migration support
- Sample fake breach data
- ETL pipeline that loads `RawEvent` and `NormalizedEvent` records

Future phases will add alert logic, incident grouping, optional LLM summaries, and the Next.js frontend.

## Project Structure

```text
breach-analytics-genai/
  .env.example
  docker-compose.yml
  backend/
    Dockerfile
    alembic.ini
    app/
      api/
        routes/
          health.py
      core/
        config.py
      db/
        base.py
        models.py
        session.py
      etl/
        extract.py
        load.py
        normalize.py
        run.py
        schemas.py
      main.py
    migrations/
      versions/
        202606150001_create_breach_analytics_tables.py
    tests/
      test_config.py
      test_etl_normalization.py
      test_health.py
      test_models.py
    requirements.txt
  data/
    auth_logs.json
    vpn_logs.csv
    cloud_audit_logs.json
    api_access_logs.csv
    endpoint_alerts.json
    README.md
  docs/
  frontend/
  scripts/
```

## Backend Setup

Prerequisite: install Python 3.11 or newer and make sure `python` works from PowerShell.

Run these commands from the project root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
python -m uvicorn app.main:app --reload
```

After the server starts, open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "breach-analytics-genai-backend"
}
```

## ETL Pipeline

The ETL pipeline reads the fake source logs in `data/`, preserves each original source record in `raw_events.raw_payload`, normalizes each source into a common event shape, and inserts those normalized records into `normalized_events`.

The normalized schema includes:

- `timestamp`
- `source_system`
- `event_type`
- `username`
- `source_ip`
- `destination_ip`
- `asset`
- `action`
- `outcome`
- `severity`
- `mitre_technique_id`
- `message`

This phase does not create alerts, correlate incidents, build frontend screens, or call an LLM.

### Run ETL Locally

These commands use Docker only for PostgreSQL, then run Alembic and ETL from your local backend virtual environment.

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up -d db

cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.etl.run --data-dir ..\data
python -m pytest
```

Confirm records were inserted:

```powershell
cd C:\Projects\breach-analytics-genai
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS raw_events FROM raw_events;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS normalized_events FROM normalized_events;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT source_system, COUNT(*) FROM normalized_events GROUP BY source_system ORDER BY source_system;"
```

### Run ETL With Docker

These commands run the backend, database, migration, ETL, and tests inside Docker.

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.etl.run --data-dir /data
docker compose exec backend python -m pytest
```

Confirm records were inserted:

```powershell
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS raw_events FROM raw_events;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS normalized_events FROM normalized_events;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT username, COUNT(*) FROM normalized_events GROUP BY username ORDER BY username;"
```

The sample dataset currently contains 49 source records. Running ETL once should insert 49 raw events and 49 normalized events. Running ETL again should skip the existing normalized events.

## Docker Setup

Prerequisites:

- Docker Desktop is installed
- Docker Desktop is running

Run these commands from the project root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

When the containers are running, open:

```text
http://127.0.0.1:8000/health
```

You can also open the FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

In a second PowerShell window, you can confirm both services are running:

```powershell
docker compose ps
```

To stop the app:

```powershell
docker compose down
```

To stop the app and remove the local PostgreSQL data volume:

```powershell
docker compose down -v
```

## Database Migrations

This phase adds the initial database schema only. It does not add ETL, detections, incident grouping logic, frontend screens, or LLM calls yet.

The initial Alembic migration creates:

- `raw_events`
- `normalized_events`
- `alerts`
- `incidents`
- `incident_events`
- `llm_summaries`

Run the migration through Docker from the project root:

```powershell
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

Confirm the migration version:

```powershell
docker compose exec backend alembic current
```

Confirm the PostgreSQL tables exist:

```powershell
docker compose exec db psql -U breach_user -d breach_analytics -c "\dt"
```

Run the backend tests inside Docker:

```powershell
docker compose exec backend python -m pytest
```

Smoke test the running API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "breach-analytics-genai-backend"
}
```
