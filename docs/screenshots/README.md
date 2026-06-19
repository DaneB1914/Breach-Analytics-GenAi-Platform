# Screenshot Guide

Use these screenshots to make the GitHub README and portfolio page easy to scan. Capture the app after running migrations, running the workflow, and generating an incident summary so the dashboard tells a complete investigation story.

## Setup Before Capturing

Run from PowerShell:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
docker compose exec backend alembic upgrade head
Invoke-RestMethod -Method Post http://127.0.0.1:8000/workflow/run-all
Invoke-RestMethod -Method Post http://127.0.0.1:8000/incidents/1/summarize
```

Open:

```text
http://localhost:3000
http://127.0.0.1:8000/docs
```

## Recommended Screenshots

| File Name | Page | What To Show |
| --- | --- | --- |
| `dashboard-overview.png` | Dashboard overview | Counts for events, alerts, incidents, summaries, and workflow context |
| `events-list.png` | Dashboard events section | Normalized telemetry from multiple source systems |
| `alerts-list.png` | Dashboard alerts section | Detection rules, severity badges, related users, and affected assets |
| `incidents-list.png` | Dashboard incidents section | Correlated incidents with status, severity, affected user, and timing |
| `incident-summary.png` | Incident detail page | Incident context with related alerts, related events, and summary controls |
| `llm-summary-1.png` | Incident detail page | Executive summary generated from incident evidence |
| `llm-summary-2.png` | Incident detail page | Technical summary and attack timeline |
| `llm-summary-3.png` | Incident detail page | Containment steps and evidence event IDs |
| `fastapi-docs-1.png` | FastAPI docs | Swagger UI overview and key endpoint groups |
| `fastapi-docs-2.png` | FastAPI docs | Workflow and incident summary endpoints |
| `fastapi-docs-3.png` | FastAPI docs | API response schemas and typed contracts |

## Capture Tips

- Use `http://localhost:3000` for frontend screenshots.
- Use `http://127.0.0.1:8000/docs` for the FastAPI docs screenshot.
- Keep the browser width wide enough to show tables clearly.
- Avoid showing local terminal windows, API keys, or private file paths.
- Save images in this folder so README links remain stable.
