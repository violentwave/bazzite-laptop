export type AutopilotSeverity = "critical" | "high" | "medium" | "low" | "info";

export type AutopilotSystemStatus = "secure" | "warning" | "critical" | "unknown";

export interface AutopilotCategoryCount {
  category: string;
  count: number;
}

export interface AutopilotOverview {
  generated_at: string;
  system_status: AutopilotSystemStatus;
  scan_status: string;
  last_scan_time: string | null;
  default_mode: string;
  policy_version: string;
  finding_count: number;
  incident_count: number;
  open_incident_count: number;
  remediation_queue_count: number;
  requires_approval_count: number;
  blocked_action_count: number;
  audit_event_count: number;
  severity_counts: Record<AutopilotSeverity, number>;
  top_categories: AutopilotCategoryCount[];
}

export interface AutopilotFinding {
  finding_id: string;
  title: string;
  description: string;
  severity: AutopilotSeverity;
  category: string;
  source: string;
  detected_at: string;
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface AutopilotIncident {
  incident_id: string;
  title: string;
  severity: AutopilotSeverity;
  status: string;
  summary: string;
  finding_count: number;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface AutopilotEvidenceBundle {
  bundle_id: string;
  source: string;
  redaction_count: number;
  created_at: string;
  persisted: boolean;
  items: Array<{
    item_id: string;
    key: string;
    value: unknown;
    redacted: boolean;
  }>;
}

export interface AutopilotAuditEvent {
  event_id?: string;
  event_type?: string;
  actor?: string;
  created_at?: string;
  incident_id?: string | null;
  evidence_bundle_id?: string | null;
  event_hash?: string;
  prev_hash?: string;
  payload?: Record<string, unknown>;
}

export interface AutopilotPolicyStatus {
  policy_version: string;
  default_mode: string;
  blocked_always: string[];
  destructive_actions: string[];
  mode_names: string[];
  allowed_path_prefixes: string[];
}

export interface AutopilotQueueItem {
  plan_id: string;
  incident_id: string;
  incident_title: string;
  priority: AutopilotSeverity;
  execution_mode: string;
  summary: string;
  action_count: number;
  requires_approval: boolean;
  blocked_actions: number;
  approval_required_actions: number;
  auto_allowed_actions: number;
  decision: string;
  safety_constraints: string[];
  generated_at: string;
}

export type SecurityAutopilotTab =
  | "overview"
  | "findings"
  | "incidents"
  | "evidence"
  | "audit"
  | "policy"
  | "remediation";
