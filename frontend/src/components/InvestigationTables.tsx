import Link from "next/link";
import { SeverityBadge } from "@/components/SeverityBadge";
import { displayValue, formatDate } from "@/lib/format";
import type { AlertRecord, EventRecord, IncidentRecord } from "@/lib/types";

export function EventsTable({
  events,
  emptyText
}: {
  events: EventRecord[];
  emptyText: string;
}) {
  if (events.length === 0) {
    return <EmptyState text={emptyText} />;
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

export function AlertsTable({
  alerts,
  emptyText
}: {
  alerts: AlertRecord[];
  emptyText: string;
}) {
  if (alerts.length === 0) {
    return <EmptyState text={emptyText} />;
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

export function IncidentsTable({
  incidents,
  emptyText,
  datasetId
}: {
  incidents: IncidentRecord[];
  emptyText: string;
  datasetId?: number;
}) {
  if (incidents.length === 0) {
    return <EmptyState text={emptyText} />;
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
          {incidents.map((incident) => {
            const href = datasetId
              ? `/uploads/${datasetId}/incidents/${incident.id}`
              : `/incidents/${incident.id}`;

            return (
              <tr key={incident.id}>
                <td>
                  <Link className="link" href={href}>
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
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty-state">
      <p className="muted">{text}</p>
    </div>
  );
}
