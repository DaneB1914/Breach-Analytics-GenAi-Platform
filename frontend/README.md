# Frontend Dashboard

Next.js dashboard for the Breach Analytics GenAI Platform.

## Setup

Run these commands from the `frontend` folder:

```powershell
Copy-Item .env.local.example .env.local -Force
npm install
npm run dev
```

The dashboard runs at:

```text
http://127.0.0.1:3000
```

The frontend expects the FastAPI backend at:

```text
http://127.0.0.1:8000
```

Change `NEXT_PUBLIC_API_BASE_URL` in `.env.local` if your backend runs elsewhere.

## Useful Scripts

```powershell
npm run dev
npm run build
npm run typecheck
```

## Views

- Dashboard overview with counts for events, alerts, incidents, and LLM summaries
- Workflow panel for ETL, detections, incident correlation, and full workflow
- Events, alerts, and incidents tables
- Incident detail view with related alerts, related events, and summary generation
