# Breach Analytics GenAI Platform

A portfolio project for a breach analytics AI/GenAI contractor role. The planned platform will ingest fake security logs, normalize them through ETL, store them in PostgreSQL, detect suspicious activity, group alerts into incidents, and optionally generate auditable incident summaries with an LLM.

## Current Phase: LLM Incident Summaries

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
- Detection engine that creates `Alert` records from normalized events
- Incident correlation engine that groups alerts into `Incident` records
- REST API endpoints for events, alerts, incidents, and backend workflow runs
- Mock-first incident summary generation stored in `LLMSummary`

Future phases will add the Next.js frontend.

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
        dependencies.py
        schemas.py
        routes/
          alerts.py
          events.py
          health.py
          incidents.py
          workflow.py
      core/
        config.py
      db/
        base.py
        models.py
        session.py
      detections/
        engine.py
        rules.py
        run.py
        schemas.py
      etl/
        extract.py
        load.py
        normalize.py
        run.py
        schemas.py
      incidents/
        correlation.py
        engine.py
        run.py
        schemas.py
      summaries/
        prompt.py
        providers.py
        schemas.py
        service.py
      main.py
    migrations/
      versions/
        202606150001_create_breach_analytics_tables.py
        202606170001_add_alert_detection_metadata.py
        202606170002_add_incident_correlation_metadata.py
        202606180001_add_llm_summary_audit_fields.py
    tests/
      test_api_endpoints.py
      test_config.py
      test_detections.py
      test_etl_normalization.py
      test_health.py
      test_incidents.py
      test_models.py
      test_summaries.py
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

## Detection Engine

The detection engine reads `normalized_events`, applies rule-based detections, and inserts findings into `alerts`.

Implemented rules:

- Brute force followed by successful login
- Successful login from unusual IP
- VPN login followed by privilege escalation
- Suspicious API data download
- Endpoint malware or credential access
- Multiple high-severity events by the same user within 24 hours

Each alert stores:

- Rule name
- Severity
- Description
- Related username
- Related asset
- Related normalized event IDs
- MITRE technique ID when applicable
- First seen and last seen timestamps

This phase does not correlate incidents, build frontend screens, or call an LLM.

### Run Detections Locally

Run migrations and ETL first, then run detections:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up -d db

cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.etl.run --data-dir ..\data
python -m app.detections.run
python -m pytest
```

Confirm alerts were inserted:

```powershell
cd C:\Projects\breach-analytics-genai
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS alerts FROM alerts;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT alert_rule_name, COUNT(*) FROM alerts GROUP BY alert_rule_name ORDER BY alert_rule_name;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT alert_rule_name, severity, related_username, related_asset, related_event_ids FROM alerts ORDER BY id;"
```

### Run Detections With Docker

Run the whole backend workflow inside Docker:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.etl.run --data-dir /data
docker compose exec backend python -m app.detections.run
docker compose exec backend python -m pytest
```

Confirm alerts were inserted:

```powershell
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS alerts FROM alerts;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT alert_rule_name, COUNT(*) FROM alerts GROUP BY alert_rule_name ORDER BY alert_rule_name;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT alert_rule_name, severity, related_username, related_asset, related_event_ids FROM alerts ORDER BY id;"
```

Running detections again should skip alerts that already exist for the same rule and related event IDs.

## Incident Correlation

The incident correlation engine reads unassigned `alerts`, groups related alerts into investigations, creates `incidents`, links alerts back to those incidents, and stores supporting normalized event IDs in `incident_events`.

Correlation considers:

- Related username
- Related asset
- A 24-hour time window
- Highest related alert severity
- Overlapping or combined related event IDs

Each incident stores:

- Title
- Severity
- Status
- Suspected attack path
- Affected user
- Affected assets
- First seen and last seen timestamps
- Description

This phase does not add API endpoints, frontend screens, or LLM calls.

### Run Incident Correlation Locally

Run migrations, ETL, detections, and then incident correlation:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up -d db

cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.etl.run --data-dir ..\data
python -m app.detections.run
python -m app.incidents.run
python -m pytest
```

Confirm incidents were inserted and linked:

```powershell
cd C:\Projects\breach-analytics-genai
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS incidents FROM incidents;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT id, title, severity, status, affected_user, affected_assets, suspected_attack_path FROM incidents ORDER BY id;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT incident_id, COUNT(*) AS alert_count FROM alerts WHERE incident_id IS NOT NULL GROUP BY incident_id ORDER BY incident_id;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT incident_id, COUNT(*) AS evidence_events FROM incident_events GROUP BY incident_id ORDER BY incident_id;"
```

### Run Incident Correlation With Docker

Run the full workflow inside Docker:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.etl.run --data-dir /data
docker compose exec backend python -m app.detections.run
docker compose exec backend python -m app.incidents.run
docker compose exec backend python -m pytest
```

Confirm incidents were inserted and linked:

```powershell
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT COUNT(*) AS incidents FROM incidents;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT id, title, severity, status, affected_user, affected_assets, suspected_attack_path FROM incidents ORDER BY id;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT incident_id, COUNT(*) AS alert_count FROM alerts WHERE incident_id IS NOT NULL GROUP BY incident_id ORDER BY incident_id;"
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT incident_id, COUNT(*) AS evidence_events FROM incident_events GROUP BY incident_id ORDER BY incident_id;"
```

Running incident correlation again should not create duplicate incidents because previously linked alerts already have `incident_id` values.

## API Endpoints

The FastAPI backend exposes read endpoints for normalized events, alerts, and incidents, plus workflow endpoints that run the backend pipeline.

Available endpoints:

- `GET /health`
- `GET /events`
- `GET /events/{event_id}`
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `GET /incidents`
- `GET /incidents/{incident_id}`
- `POST /incidents/{incident_id}/summarize`
- `GET /incidents/{incident_id}/summary`
- `POST /workflow/etl`
- `POST /workflow/detections`
- `POST /workflow/incidents`
- `POST /workflow/run-all`

Useful filters:

- `/events`: `skip`, `limit`, `severity`, `username`, `source_system`, `event_type`, `start_date`, `end_date`
- `/alerts`: `skip`, `limit`, `severity`, `related_username`, `alert_rule_name`, `incident_id`
- `/incidents`: `skip`, `limit`, `severity`, `status`, `affected_user`, `start_date`, `end_date`

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

### Run Full Workflow Through The API

Start the app, apply migrations, then trigger the workflow through FastAPI:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
Invoke-RestMethod -Method Post http://127.0.0.1:8000/workflow/run-all
```

You can also run each step separately:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/workflow/etl
Invoke-RestMethod -Method Post http://127.0.0.1:8000/workflow/detections
Invoke-RestMethod -Method Post http://127.0.0.1:8000/workflow/incidents
```

Browse data through the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod "http://127.0.0.1:8000/events?username=alex.morgan&limit=5"
Invoke-RestMethod "http://127.0.0.1:8000/alerts?severity=high"
Invoke-RestMethod "http://127.0.0.1:8000/incidents?status=open"
Invoke-RestMethod http://127.0.0.1:8000/incidents/1
```

Run API tests inside Docker:

```powershell
docker compose exec backend python -m pytest
```

## LLM Incident Summaries

The summary feature generates an auditable breach investigation summary for one incident and stores it in `llm_summaries`.

For a given `incident_id`, the backend retrieves:

- Incident details
- Related alerts
- Related normalized events
- Evidence event IDs from `incident_events`

The stored summary includes:

- Executive summary
- Technical summary
- Attack timeline
- Affected users
- Affected assets
- Suspected attack path
- Recommended containment steps
- Event IDs used as evidence

### Mock Mode

`OPENAI_API_KEY` is optional. If it is missing, the app uses a deterministic mock summarizer. Mock mode exists so the project works in local development, CI, portfolio demos, and Docker without paid API access or network dependencies.

The provider interface is isolated in `backend/app/summaries/`, so a real OpenAI-backed provider can be added later without changing the API routes or database model.

### Auditable Behavior

The summarizer must not invent evidence. It builds summaries only from incident, alert, and normalized event data already stored in the database. The generated summary stores `evidence_event_ids` so an analyst can trace summary claims back to the source events.

### Run Summarization In `/docs`

Start the backend and open:

```text
http://127.0.0.1:8000/docs
```

Run the full workflow first with:

```text
POST /workflow/run-all
```

Then generate and retrieve a summary:

```text
POST /incidents/1/summarize
GET /incidents/1/summary
```

### Run Summarization With PowerShell

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
Invoke-RestMethod -Method Post http://127.0.0.1:8000/workflow/run-all
Invoke-RestMethod -Method Post http://127.0.0.1:8000/incidents/1/summarize
Invoke-RestMethod http://127.0.0.1:8000/incidents/1/summary
```

Confirm summaries were stored:

```powershell
docker compose exec db psql -U breach_user -d breach_analytics -c "SELECT id, incident_id, model_name, evidence_event_ids FROM llm_summaries ORDER BY id;"
```

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

Migrations currently create the core breach analytics schema, add alert metadata used by the detection engine, add incident metadata used by correlation, and add auditable fields for stored incident summaries. They do not add frontend screens yet.

The initial Alembic migration creates:

- `raw_events`
- `normalized_events`
- `alerts`
- `incidents`
- `incident_events`
- `llm_summaries`

The second migration adds detection metadata columns to `alerts`.
The third migration adds correlation metadata columns to `incidents`.
The fourth migration adds auditable summary fields to `llm_summaries`.

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
