import Link from "next/link";
import { SeverityBadge } from "@/components/SeverityBadge";
import { UploadPanel } from "@/components/UploadPanel";
import { WorkflowPanel } from "@/components/WorkflowPanel";
import { displayValue, formatDate } from "@/lib/format";
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
        <EventsTable events={data.events.slice(0, 12)} />
      </section>

      <section className="section" id="alerts">
        <div className="section-header">
          <div>
            <h2>Alerts</h2>
            <p className="section-note">Rule findings created by the detection engine.</p>
          </div>
        </div>
        <AlertsTable alerts={data.alerts.slice(0, 12)} />
      </section>

      <section className="section" id="incidents">
        <div className="section-header">
          <div>
            <h2>Incidents</h2>
            <p className="section-note">Correlated investigations with linked alerts and evidence events.</p>
          </div>
        </div>
        <IncidentsTable incidents={data.incidents.slice(0, 12)} />
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

function EventsTable({ events }: { events: EventRecord[] }) {
  if (events.length === 0) {
    return <EmptyState text="No normalized events loaded yet. Run the ETL workflow to populate this table." />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Source</th>
            <th>Event Type</th>
            <th>User</th>
            <th>Asset</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{formatDate(event.event_timestamp)}</td>
              <td>{event.source_system}</td>
              <td>{event.event_type}</td>
              <td>{displayValue(event.username)}</td>
              <td>{displayValue(event.asset)}</td>
              <td>
                <SeverityBadge severity={event.severity} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AlertsTable({ alerts }: { alerts: AlertRecord[] }) {
  if (alerts.length === 0) {
    return <EmptyState text="No alerts available yet. Run detections after ETL completes." />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rule</th>
            <th>Severity</th>
            <th>User</th>
            <th>Asset</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td>{alert.alert_rule_name}</td>
              <td>
                <SeverityBadge severity={alert.severity} />
              </td>
              <td>{displayValue(alert.related_username)}</td>
              <td>{displayValue(alert.related_asset)}</td>
              <td>{alert.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IncidentsTable({ incidents }: { incidents: IncidentRecord[] }) {
  if (incidents.length === 0) {
    return <EmptyState text="No incidents available yet. Run incident correlation after alerts are created." />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Affected User</th>
            <th>First Seen</th>
            <th>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id}>
              <td>
                <Link className="link" href={`/incidents/${incident.id}`}>
                  {incident.title}
                </Link>
              </td>
              <td>
                <SeverityBadge severity={incident.severity} />
              </td>
              <td>{incident.status}</td>
              <td>{displayValue(incident.affected_user)}</td>
              <td>{formatDate(incident.first_seen)}</td>
              <td>{formatDate(incident.last_seen)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="panel">
      <div className="panel-body">
        <p className="muted">{text}</p>
      </div>
    </div>
  );
}
