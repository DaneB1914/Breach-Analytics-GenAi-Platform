import Link from "next/link";
import { DatasetWorkflowPanel } from "@/components/DatasetWorkflowPanel";
import { AlertsTable, EventsTable, IncidentsTable } from "@/components/InvestigationTables";
import { displayValue, formatDate } from "@/lib/format";
import {
  getDatasetAlerts,
  getDatasetEvents,
  getDatasetIncidents,
  getUpload
} from "@/lib/api";
import type {
  AlertRecord,
  EventRecord,
  IncidentRecord,
  UploadedDatasetRecord
} from "@/lib/types";

export const dynamic = "force-dynamic";

type DatasetPageData = {
  dataset: UploadedDatasetRecord | null;
  events: EventRecord[];
  alerts: AlertRecord[];
  incidents: IncidentRecord[];
  error: string | null;
};

export default async function DatasetDetailPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const datasetId = Number(id);
  const data = await loadDatasetPageData(datasetId);

  if (data.error || !data.dataset) {
    return (
      <main className="page">
        <Link className="link" href="/#uploads">
          Back to uploads
        </Link>
        <div className="message error">{data.error || "Dataset not found."}</div>
      </main>
    );
  }

  const dataset = data.dataset;
  const needsNormalization = dataset.status === "uploaded";
  const needsAnalysis = dataset.status === "normalized" && data.incidents.length === 0;

  return (
    <main className="page">
      <section className="page-header">
        <Link className="link" href="/#uploads">
          Back to uploads
        </Link>
        <div className="eyebrow">Active Dataset</div>
        <h1>{dataset.name}</h1>
        <p className="lede">
          {dataset.description || "Analyst-uploaded security telemetry investigation."}
        </p>
        <div className="active-dataset">
          Investigation scope: <strong>{dataset.name}</strong>
        </div>
      </section>

      {needsNormalization ? (
        <div className="message warning">
          This dataset has not been normalized yet. Select Normalize Dataset or run the full dataset workflow.
        </div>
      ) : null}
      {needsAnalysis ? (
        <div className="message warning">
          Normalized events are available, but detections and incident correlation have not produced an incident yet.
        </div>
      ) : null}

      <section className="split-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Dataset Details</h2>
            <span className="badge unknown">{dataset.status.replaceAll("_", " ")}</span>
          </div>
          <div className="panel-body">
            <div className="detail-list">
              <Detail label="Source Type" value={dataset.source_type} />
              <Detail label="Uploaded File" value={dataset.files[0]?.original_filename} />
              <Detail label="Record Count" value={String(dataset.record_count)} />
              <Detail label="Created" value={formatDate(dataset.created_at)} />
            </div>
          </div>
        </div>
        <DatasetWorkflowPanel datasetId={dataset.id} datasetName={dataset.name} />
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Events</h2>
            <p className="section-note">Normalized records owned by this dataset.</p>
          </div>
        </div>
        <EventsTable
          events={data.events}
          emptyText="No normalized events exist for this dataset yet."
        />
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Alerts</h2>
            <p className="section-note">Detection findings created only from this dataset.</p>
          </div>
        </div>
        <AlertsTable
          alerts={data.alerts}
          emptyText="No alerts exist for this dataset yet. Run the dataset workflow after normalization."
        />
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Incidents</h2>
            <p className="section-note">Correlated investigations isolated to this dataset.</p>
          </div>
        </div>
        <IncidentsTable
          incidents={data.incidents}
          datasetId={dataset.id}
          emptyText="No incidents exist for this dataset yet."
        />
      </section>
    </main>
  );
}

async function loadDatasetPageData(datasetId: number): Promise<DatasetPageData> {
  try {
    const [dataset, events, alerts, incidents] = await Promise.all([
      getUpload(datasetId),
      getDatasetEvents(datasetId),
      getDatasetAlerts(datasetId),
      getDatasetIncidents(datasetId)
    ]);
    return { dataset, events, alerts, incidents, error: null };
  } catch (error) {
    return {
      dataset: null,
      events: [],
      alerts: [],
      incidents: [],
      error:
        error instanceof Error
          ? `Could not load dataset ${datasetId}: ${error.message}`
          : `Could not load dataset ${datasetId}.`
    };
  }
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="detail-item">
      <div className="detail-label">{label}</div>
      <div className="detail-value">{displayValue(value)}</div>
    </div>
  );
}
