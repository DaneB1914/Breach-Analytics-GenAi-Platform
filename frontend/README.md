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
http://localhost:3000
```

The frontend expects the FastAPI backend at:

```text
http://localhost:8000
```

Change `NEXT_PUBLIC_API_BASE_URL` in `.env.local` if your browser should call a different backend URL. `FRONTEND_SERVER_API_BASE_URL` is used by Next.js server-side rendering.

## Docker

The root Docker Compose file can run PostgreSQL, FastAPI, and this frontend together:

```powershell
cd C:\Projects\breach-analytics-genai
Copy-Item .env.example .env -Force
docker compose up --build -d
```

Open:

```text
http://localhost:3000
```

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
