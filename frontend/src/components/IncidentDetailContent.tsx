import Link from "next/link";
import { ReportExportButton } from "@/components/ReportExportButton";
import { SeverityBadge } from "@/components/SeverityBadge";
import { SummaryPanel } from "@/components/SummaryPanel";
import { displayValue, formatDate } from "@/lib/format";
import type { IncidentDetail, LLMSummary } from "@/lib/types";

export function IncidentDetailContent({
  incident,
  summary,
  backHref,
  backLabel,
  datasetId,
  datasetName
}: {
  incident: IncidentDetail;
  summary: LLMSummary | null;
  backHref: string;
  backLabel: string;
  datasetId?: number;
  datasetName?: string;
}) {
  return (
    <main className="page">
      <section className="page-header">
        <Link className="link" href={backHref}>
          {backLabel}
        </Link>
        <div className="eyebrow">{datasetName ? "Dataset Incident" : "Demo Incident"}</div>
        <h1>{incident.title}</h1>
        <p className="lede">{incident.description || "Correlated incident from alert and event evidence."}</p>
        {datasetName ? (
          <div className="active-dataset">
            Active dataset: <strong>{datasetName}</strong>
          </div>
        ) : null}
        <ReportExportButton incidentId={incident.id} datasetId={datasetId} />
      </section>

      <section className="split-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Incident Details</h2>
            <SeverityBadge severity={incident.severity} />
          </div>
          <div className="panel-body">
            <div className="detail-list">
              <Detail label="Status" value={incident.status} />
              <Detail label="Affected User" value={incident.affected_user} />
              <Detail label="Affected Assets" value={incident.affected_assets.join(", ")} />
              <Detail label="First Seen" value={formatDate(incident.first_seen)} />
              <Detail label="Last Seen" value={formatDate(incident.last_seen)} />
              <Detail label="Attack Path" value={incident.suspected_attack_path} />
            </div>
          </div>
        </div>

        <SummaryPanel
          incidentId={incident.id}
          initialSummary={summary}
          datasetId={datasetId}
        />
      </section>

      <section className="section">
        <div className="section-header">
          <h2>Related Alerts</h2>
          <p className="section-note">{incident.alerts.length} alerts linked to this incident.</p>
        </div>
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
              {incident.alerts.map((alert) => (
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
      </section>

      <section className="section">
        <div className="section-header">
          <h2>Related Events</h2>
          <p className="section-note">{incident.related_events.length} normalized events used as evidence.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Time</th>
                <th>Source</th>
                <th>Event Type</th>
                <th>User</th>
                <th>Asset</th>
              </tr>
            </thead>
            <tbody>
              {incident.related_events.map((event) => (
                <tr key={event.id}>
                  <td className="mono">{event.id}</td>
                  <td>{formatDate(event.event_timestamp)}</td>
                  <td>{event.source_system}</td>
                  <td>{event.event_type}</td>
                  <td>{displayValue(event.username)}</td>
                  <td>{displayValue(event.asset)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="detail-item">
      <div className="detail-label">{label}</div>
      <div className="detail-value">{displayValue(value)}</div>
    </div>
  );
}
