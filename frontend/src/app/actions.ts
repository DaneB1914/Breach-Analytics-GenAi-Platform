"use server";

import { runWorkflow, summarizeIncident } from "@/lib/api";

export async function runWorkflowAction(step: "etl" | "detections" | "incidents" | "run-all") {
  try {
    const result = await runWorkflow(step);
    return { ok: true, message: result.message, details: result.details };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Workflow request failed",
      details: {}
    };
  }
}

export async function summarizeIncidentAction(incidentId: number) {
  try {
    const summary = await summarizeIncident(incidentId);
    return { ok: true, summary, message: "Incident summary generated" };
  } catch (error) {
    return {
      ok: false,
      summary: null,
      message: error instanceof Error ? error.message : "Summary request failed"
    };
  }
}
