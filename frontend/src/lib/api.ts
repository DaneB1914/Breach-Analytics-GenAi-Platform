import type {
  AlertRecord,
  EventRecord,
  IncidentDetail,
  IncidentRecord,
  LLMSummary,
  UploadedDatasetRecord,
  WorkflowResponse
} from "./types";

const API_BASE_URL =
  process.env.FRONTEND_SERVER_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export async function getEvents(limit = 50): Promise<EventRecord[]> {
  return fetchApi<EventRecord[]>(`/events?limit=${limit}`);
}

export async function getAlerts(limit = 50): Promise<AlertRecord[]> {
  return fetchApi<AlertRecord[]>(`/alerts?limit=${limit}`);
}

export async function getIncidents(limit = 50): Promise<IncidentRecord[]> {
  return fetchApi<IncidentRecord[]>(`/incidents?limit=${limit}`);
}

export async function getUploads(): Promise<UploadedDatasetRecord[]> {
  return fetchApi<UploadedDatasetRecord[]>("/uploads");
}

export async function getUpload(datasetId: number): Promise<UploadedDatasetRecord> {
  return fetchApi<UploadedDatasetRecord>(`/uploads/${datasetId}`);
}

export async function getDatasetEvents(datasetId: number, limit = 500): Promise<EventRecord[]> {
  return fetchApi<EventRecord[]>(`/uploads/${datasetId}/events?limit=${limit}`);
}

export async function getDatasetAlerts(datasetId: number, limit = 500): Promise<AlertRecord[]> {
  return fetchApi<AlertRecord[]>(`/uploads/${datasetId}/alerts?limit=${limit}`);
}

export async function getDatasetIncidents(
  datasetId: number,
  limit = 500
): Promise<IncidentRecord[]> {
  return fetchApi<IncidentRecord[]>(`/uploads/${datasetId}/incidents?limit=${limit}`);
}

export async function getIncident(incidentId: number): Promise<IncidentDetail> {
  return fetchApi<IncidentDetail>(`/incidents/${incidentId}`);
}

export async function getDatasetIncident(
  datasetId: number,
  incidentId: number
): Promise<IncidentDetail> {
  return fetchApi<IncidentDetail>(`/uploads/${datasetId}/incidents/${incidentId}`);
}

export async function getIncidentReport(
  incidentId: number,
  datasetId?: number
): Promise<{ content: string; filename: string }> {
  const path = datasetId
    ? `/uploads/${datasetId}/incidents/${incidentId}/report`
    : `/incidents/${incidentId}/report`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store"
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(detail || "Incident report request failed", response.status);
  }

  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);

  return {
    content: await response.text(),
    filename: filenameMatch?.[1] || `incident-${incidentId}-report.md`
  };
}

export async function summarizeIncident(incidentId: number): Promise<LLMSummary> {
  return fetchApi<LLMSummary>(`/incidents/${incidentId}/summarize`, { method: "POST" });
}

export async function summarizeDatasetIncident(
  datasetId: number,
  incidentId: number
): Promise<LLMSummary> {
  return fetchApi<LLMSummary>(`/uploads/${datasetId}/incidents/${incidentId}/summarize`, {
    method: "POST"
  });
}

export async function getIncidentSummary(incidentId: number): Promise<LLMSummary | null> {
  try {
    return await fetchApi<LLMSummary>(`/incidents/${incidentId}/summary`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function getDatasetIncidentSummary(
  datasetId: number,
  incidentId: number
): Promise<LLMSummary | null> {
  try {
    return await fetchApi<LLMSummary>(`/uploads/${datasetId}/incidents/${incidentId}/summary`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function runWorkflow(
  step: "etl" | "detections" | "incidents" | "run-all"
): Promise<WorkflowResponse> {
  return fetchApi<WorkflowResponse>(`/workflow/${step}`, { method: "POST" });
}

export async function uploadDataset(formData: FormData): Promise<UploadedDatasetRecord> {
  return fetchApi<UploadedDatasetRecord>("/uploads", {
    method: "POST",
    body: formData
  });
}

export async function normalizeUploadedDataset(datasetId: number): Promise<WorkflowResponse> {
  return fetchApi<WorkflowResponse>(`/uploads/${datasetId}/normalize`, { method: "POST" });
}

export async function runUploadedDatasetWorkflow(datasetId: number): Promise<WorkflowResponse> {
  return fetchApi<WorkflowResponse>(`/uploads/${datasetId}/run-workflow`, { method: "POST" });
}

export async function getSummaryCount(incidents: IncidentRecord[]): Promise<number> {
  const results = await Promise.allSettled(
    incidents.map((incident) => getIncidentSummary(incident.id))
  );

  return results.filter((result) => result.status === "fulfilled" && result.value !== null).length;
}

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers || {})
    }
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(detail || `FastAPI request failed for ${path}`, response.status);
  }

  return response.json() as Promise<T>;
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = await response.json();
    return typeof payload.detail === "string" ? payload.detail : null;
  } catch {
    return null;
  }
}
