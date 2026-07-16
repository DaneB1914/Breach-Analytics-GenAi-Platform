"use server";

import {
  getIncidentReport,
  normalizeUploadedDataset,
  previewDatasetMappings,
  runUploadedDatasetWorkflow,
  runWorkflow,
  saveDatasetMappings,
  summarizeDatasetIncident,
  summarizeIncident,
  uploadDataset
} from "@/lib/api";
import type { DatasetFieldMappingInput } from "@/lib/types";

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

export async function summarizeIncidentAction(incidentId: number, datasetId?: number) {
  try {
    const summary = datasetId
      ? await summarizeDatasetIncident(datasetId, incidentId)
      : await summarizeIncident(incidentId);
    return { ok: true, summary, message: "Incident summary generated" };
  } catch (error) {
    return {
      ok: false,
      summary: null,
      message: error instanceof Error ? error.message : "Summary request failed"
    };
  }
}

export async function exportIncidentReportAction(incidentId: number, datasetId?: number) {
  try {
    const report = await getIncidentReport(incidentId, datasetId);
    return {
      ok: true,
      content: report.content,
      filename: report.filename,
      message: "Incident report downloaded"
    };
  } catch (error) {
    return {
      ok: false,
      content: null,
      filename: null,
      message: error instanceof Error ? error.message : "Report export failed"
    };
  }
}

export async function uploadDatasetAction(formData: FormData) {
  try {
    const dataset = await uploadDataset(formData);
    return {
      ok: true,
      dataset,
      message: `Uploaded dataset "${dataset.name}" with ${dataset.record_count} records.`
    };
  } catch (error) {
    return {
      ok: false,
      dataset: null,
      message: error instanceof Error ? error.message : "Upload request failed"
    };
  }
}

export async function normalizeUploadedDatasetAction(datasetId: number) {
  try {
    const result = await normalizeUploadedDataset(datasetId);
    return { ok: true, message: result.message, details: result.details };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Normalize request failed",
      details: {}
    };
  }
}

export async function saveDatasetMappingsAction(
  datasetId: number,
  mappings: DatasetFieldMappingInput[]
) {
  try {
    const savedMappings = await saveDatasetMappings(datasetId, mappings);
    return {
      ok: true,
      mappings: savedMappings,
      message: `Saved ${savedMappings.length} field mappings.`
    };
  } catch (error) {
    return {
      ok: false,
      mappings: [],
      message: error instanceof Error ? error.message : "Save mapping request failed"
    };
  }
}

export async function previewDatasetMappingsAction(
  datasetId: number,
  mappings: DatasetFieldMappingInput[]
) {
  try {
    const preview = await previewDatasetMappings(datasetId, mappings);
    return { ok: true, preview, message: "Normalized preview generated." };
  } catch (error) {
    return {
      ok: false,
      preview: null,
      message: error instanceof Error ? error.message : "Mapping preview request failed"
    };
  }
}

export async function runUploadedDatasetWorkflowAction(datasetId: number) {
  try {
    const result = await runUploadedDatasetWorkflow(datasetId);
    return { ok: true, message: result.message, details: result.details };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Uploaded workflow request failed",
      details: {}
    };
  }
}
