import type {
  AlertRecord,
  EventRecord,
  IncidentDetail,
  IncidentRecord,
  LLMSummary,
  WorkflowResponse
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

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

export async function getIncident(incidentId: number): Promise<IncidentDetail> {
  return fetchApi<IncidentDetail>(`/incidents/${incidentId}`);
}

export async function summarizeIncident(incidentId: number): Promise<LLMSummary> {
  return fetchApi<LLMSummary>(`/incidents/${incidentId}/summarize`, { method: "POST" });
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

export async function runWorkflow(
  step: "etl" | "detections" | "incidents" | "run-all"
): Promise<WorkflowResponse> {
  return fetchApi<WorkflowResponse>(`/workflow/${step}`, { method: "POST" });
}

export async function getSummaryCount(incidents: IncidentRecord[]): Promise<number> {
  const results = await Promise.allSettled(
    incidents.map((incident) => getIncidentSummary(incident.id))
  );

  return results.filter((result) => result.status === "fulfilled" && result.value !== null).length;
}

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });

  if (!response.ok) {
    throw new ApiError(`FastAPI request failed for ${path}`, response.status);
  }

  return response.json() as Promise<T>;
}
