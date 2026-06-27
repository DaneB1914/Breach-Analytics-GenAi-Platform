export type Severity = "critical" | "high" | "medium" | "low" | string | null;

export type EventRecord = {
  id: number;
  raw_event_id: number;
  uploaded_dataset_id: number | null;
  normalized_at: string | null;
  event_timestamp: string | null;
  source_system: string;
  event_type: string;
  username: string | null;
  source_ip: string | null;
  destination_ip: string | null;
  asset: string | null;
  action: string | null;
  outcome: string | null;
  severity: Severity;
  mitre_technique_id: string | null;
  normalized_message: string | null;
};

export type AlertRecord = {
  id: number;
  normalized_event_id: number;
  incident_id: number | null;
  created_at: string | null;
  alert_rule_name: string;
  severity: string;
  description: string;
  related_username: string | null;
  related_asset: string | null;
  related_event_ids: number[];
  mitre_technique_id: string | null;
  first_seen: string | null;
  last_seen: string | null;
  normalized_message: string;
};

export type IncidentRecord = {
  id: number;
  created_at: string | null;
  updated_at: string | null;
  status: string;
  severity: Severity;
  title: string;
  suspected_attack_path: string | null;
  description: string | null;
  affected_user: string | null;
  affected_assets: string[];
  first_seen: string | null;
  last_seen: string | null;
};

export type IncidentDetail = IncidentRecord & {
  alerts: AlertRecord[];
  related_events: EventRecord[];
};

export type LLMSummary = {
  id: number;
  incident_id: number;
  created_at: string | null;
  model_name: string | null;
  executive_summary: string;
  technical_summary: string;
  attack_timeline: Array<Record<string, unknown>>;
  affected_users: string[];
  affected_assets: string[];
  suspected_attack_path: string | null;
  recommended_containment_steps: string[];
  evidence_event_ids: number[];
};

export type WorkflowResponse = {
  status: string;
  message: string;
  details: Record<string, unknown>;
};

export type UploadedFileRecord = {
  id: number;
  dataset_id: number;
  original_filename: string;
  stored_path: string;
  content_type: string | null;
  size_bytes: number;
  uploaded_at: string | null;
};

export type UploadedDatasetRecord = {
  id: number;
  name: string;
  description: string | null;
  created_at: string | null;
  status: string;
  source_type: string;
  record_count: number;
  files: UploadedFileRecord[];
};
