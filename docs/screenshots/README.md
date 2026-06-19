# Screenshot Guide

Use these screenshots to make the GitHub README and portfolio page easy to scan. Capture the app after running migrations and the full workflow so events, alerts, incidents, and summaries are populated.

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
| `dashboard-overview.png` | Dashboard overview | Counts for events, alerts, incidents, summaries, plus workflow context |
| `events-list.png` | Dashboard events section | Normalized events from multiple source systems |
| `alerts-list.png` | Dashboard alerts section | Alert rules, severity badges, related users, and related assets |
| `incident-detail.png` | Incident detail page | Incident metadata with related alerts and evidence events |
| `llm-summary-panel.png` | Incident detail page | Generated executive summary, technical summary, timeline, and evidence IDs |
| `fastapi-docs.png` | FastAPI docs | Swagger UI with events, alerts, incidents, workflow, and summary endpoints |

## Capture Tips

- Use `http://localhost:3000` for frontend screenshots.
- Use `http://127.0.0.1:8000/docs` for the FastAPI docs screenshot.
- Keep the browser width wide enough to show tables clearly.
- Avoid showing local terminal windows, API keys, or private file paths.
- Save images in this folder so README links are easy to add later.
