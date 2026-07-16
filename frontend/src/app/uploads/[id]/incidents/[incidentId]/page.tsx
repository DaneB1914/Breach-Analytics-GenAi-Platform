import Link from "next/link";
import { IncidentDetailContent } from "@/components/IncidentDetailContent";
import {
  getDatasetIncident,
  getDatasetIncidentSummary,
  getUpload
} from "@/lib/api";
import type { IncidentDetail, LLMSummary, UploadedDatasetRecord } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function DatasetIncidentDetailPage({
  params
}: {
  params: Promise<{ id: string; incidentId: string }>;
}) {
  const { id, incidentId: incidentIdValue } = await params;
  const datasetId = Number(id);
  const incidentId = Number(incidentIdValue);
  const data = await loadPageData(datasetId, incidentId);

  if (data.error || !data.dataset || !data.incident) {
    return (
      <main className="page">
        <Link className="link" href={`/uploads/${datasetId}`}>
          Back to dataset
        </Link>
        <div className="message error">{data.error || "Incident not found in this dataset."}</div>
      </main>
    );
  }

  return (
    <IncidentDetailContent
      incident={data.incident}
      summary={data.summary}
      backHref={`/uploads/${datasetId}`}
      backLabel={`Back to ${data.dataset.name}`}
      datasetId={datasetId}
      datasetName={data.dataset.name}
    />
  );
}

async function loadPageData(
  datasetId: number,
  incidentId: number
): Promise<{
  dataset: UploadedDatasetRecord | null;
  incident: IncidentDetail | null;
  summary: LLMSummary | null;
  error: string | null;
}> {
  try {
    const [dataset, incident, summary] = await Promise.all([
      getUpload(datasetId),
      getDatasetIncident(datasetId, incidentId),
      getDatasetIncidentSummary(datasetId, incidentId)
    ]);
    return { dataset, incident, summary, error: null };
  } catch (error) {
    return {
      dataset: null,
      incident: null,
      summary: null,
      error:
        error instanceof Error
          ? `Could not load incident ${incidentId}: ${error.message}`
          : `Could not load incident ${incidentId}.`
    };
  }
}
