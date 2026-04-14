/** Project + Workflow + Phase Panels types */

export type PhaseStatus = "planned" | "ready" | "in_progress" | "completed" | "blocked";
export type ReadinessStatus = "ready" | "blocked" | "degraded" | "unknown";
export type WorkflowStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type PreflightGateStatus = "pass" | "fail" | "warn";

/** Current phase information */
export interface PhaseInfo {
  phase_number: number | null;
  phase_name: string | null;
  status: string | null;
  readiness: ReadinessStatus;
  blockers: string[];
  next_action: string | null;
  risk_tier: string | null;
  backend: string | null;
}

/** Workflow run summary */
export interface WorkflowRun {
  run_id: string;
  workflow_name: string;
  status: WorkflowStatus;
  started_at: string;
  completed_at: string | null;
  triggered_by: string;
  step_count: number;
  current_step: number | null;
  error_message: string | null;
}

/** Artifact/evidence summary */
export interface ArtifactInfo {
  name: string;
  type: string;
  path: string;
  size_bytes: number;
  created_at: string;
  source_phase: string | null;
}

/** Phase timeline entry */
export interface PhaseTimelineEntry {
  number: number;
  name: string;
  status: PhaseStatus;
  doc_file: string;
  modified: string;
}

/** Complete project context */
export interface ProjectContext {
  current_phase: PhaseInfo | null;
  workflow_count: number;
  artifact_count: number;
  recommendations: string[];
  preflight_status: PreflightGateStatus;
  generated_at: string;
}

/** Preflight summary from P75 */
export interface PreflightSummary {
  schema_version: string;
  generated_at: string;
  gate_status: PreflightGateStatus;
  gate_reason: string;
  code_files_count: number;
  impact_score: number | null;
  health_status: string;
  health_issues: string[];
}

/** Project workflow state */
export interface ProjectWorkflowState {
  context: ProjectContext | null;
  workflows: WorkflowRun[];
  timeline: PhaseTimelineEntry[];
  artifacts: ArtifactInfo[];
  isLoading: boolean;
  error: string | null;
}
