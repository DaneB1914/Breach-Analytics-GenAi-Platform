import { AlertsTable, EventsTable, IncidentsTable } from "@/components/InvestigationTables";
import { UploadPanel } from "@/components/UploadPanel";
import { WorkflowPanel } from "@/components/WorkflowPanel";
import { getAlerts, getEvents, getIncidents, getSummaryCount, getUploads } from "@/lib/api";
import type { AlertRecord, EventRecord, IncidentRecord, UploadedDatasetRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

type DashboardData = {
  events: EventRecord[];
  alerts: AlertRecord[];
  incidents: IncidentRecord[];
  uploads: UploadedDatasetRecord[];
  summaryCount: number;
  error: string | null;
};

export default async function DashboardPage() {
  const data = await loadDashboardData();

  return (
    <main className="page">
      <section className="page-header">
        <div className="eyebrow">Breach Analytics Workflow</div>
        <h1>Investigate fake breach activity from raw logs to auditable incident summaries.</h1>
        <p className="lede">
          This dashboard demonstrates the full-stack workflow: ingest realistic fake security logs,
          normalize them, run detection rules, correlate incidents, and generate mock LLM summaries
          that preserve evidence event IDs.
        </p>
      </section>

      {data.error ? <div className="message error">{data.error}</div> : null}

      <section className="metrics-grid" aria-label="Dashboard counts">
        <Metric label="Normalized events" value={data.events.length} />
        <Metric label="Alerts" value={data.alerts.length} />
        <Metric label="Incidents" value={data.incidents.length} />
        <Metric label="LLM summaries" value={data.summaryCount} />
        <Metric label="Uploaded datasets" value={data.uploads.length} />
      </section>

      <section className="section">
        <WorkflowPanel />
      </section>

      <section className="section">
        <UploadPanel datasets={data.uploads} />
      </section>

      <section className="section" id="events">
        <div className="section-header">
          <div>
            <h2>Events</h2>
            <p className="section-note">Latest normalized events from the FastAPI backend.</p>
          </div>
        </div>
        <EventsTable
          events={data.events.slice(0, 12)}
          emptyText="No normalized demo events loaded yet. Run the ETL workflow to populate this table."
        />
      </section>

      <section className="section" id="alerts">
        <div className="section-header">
          <div>
            <h2>Alerts</h2>
            <p className="section-note">Rule findings created by the detection engine.</p>
          </div>
        </div>
        <AlertsTable
          alerts={data.alerts.slice(0, 12)}
          emptyText="No demo alerts available yet. Run detections after ETL completes."
        />
      </section>

      <section className="section" id="incidents">
        <div className="section-header">
          <div>
            <h2>Incidents</h2>
            <p className="section-note">Correlated investigations with linked alerts and evidence events.</p>
          </div>
        </div>
        <IncidentsTable
          incidents={data.incidents.slice(0, 12)}
          emptyText="No demo incidents available yet. Run incident correlation after alerts are created."
        />
      </section>
    </main>
  );
}

async function loadDashboardData(): Promise<DashboardData> {
  try {
    const [events, alerts, incidents, uploads] = await Promise.all([
      getEvents(500),
      getAlerts(500),
      getIncidents(500),
      getUploads()
    ]);
    const summaryCount = await getSummaryCount(incidents);

    return { events, alerts, incidents, uploads, summaryCount, error: null };
  } catch (error) {
    return {
      events: [],
      alerts: [],
      incidents: [],
      uploads: [],
      summaryCount: 0,
      error:
        error instanceof Error
          ? `Could not reach the FastAPI backend: ${error.message}`
          : "Could not reach the FastAPI backend."
    };
  }
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}
