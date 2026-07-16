import Link from "next/link";
import { IncidentDetailContent } from "@/components/IncidentDetailContent";
import { getIncident, getIncidentSummary } from "@/lib/api";
import type { IncidentDetail, LLMSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function IncidentDetailPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const incidentId = Number(id);
  const { incident, summary, error } = await loadIncidentPageData(incidentId);

  if (error || !incident) {
    return (
      <main className="page">
        <Link className="link" href="/">
          Back to dashboard
        </Link>
        <div className="message error">{error || "Incident not found."}</div>
      </main>
    );
  }

  return (
    <IncidentDetailContent
      incident={incident}
      summary={summary}
      backHref="/"
      backLabel="Back to dashboard"
    />
  );
}

async function loadIncidentPageData(
  incidentId: number
): Promise<{ incident: IncidentDetail | null; summary: LLMSummary | null; error: string | null }> {
  try {
    const incident = await getIncident(incidentId);
    const summary = await getIncidentSummary(incidentId);
    return { incident, summary, error: null };
  } catch (error) {
    return {
      incident: null,
      summary: null,
      error:
        error instanceof Error
          ? `Could not load incident ${incidentId}: ${error.message}`
          : `Could not load incident ${incidentId}.`
    };
  }
}
