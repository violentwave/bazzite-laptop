/** Security Ops Center types */

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type AlertCategory = "scan" | "cve" | "provider" | "timer" | "system";
export type ScanStatus = "clean" | "infected" | "error" | "pending";
export type SystemStatus = "secure" | "warning" | "critical" | "unknown";
export type ProviderIssueType = "auth_failed" | "timeout" | "error" | "degraded";

/** Security alert data structure */
export interface SecurityAlert {
  id: string;
  severity: Severity;
  category: AlertCategory;
  title: string;
  description: string;
  timestamp: string;
  source: string;
  acknowledged: boolean;
  related_action?: string;
}

/** Scan finding data structure */
export interface ScanFinding {
  id: string;
  scan_type: string;
  status: ScanStatus;
  threats_found: number;
  files_scanned: number;
  timestamp: string;
  details?: string;
}

/** CVE risk data structure */
export interface CVERisk {
  id: string;
  package: string;
  severity: Severity;
  cve_id: string;
  description: string;
  fixed_version?: string;
  timestamp: string;
}

/** Provider health issue data structure */
export interface ProviderHealthIssue {
  provider: string;
  issue_type: ProviderIssueType;
  description: string;
  timestamp: string;
  consecutive_failures: number;
  auth_broken: boolean;
}

/** Timer/workflow anomaly data structure */
export interface TimerAnomaly {
  timer_name: string;
  expected_interval: string;
  last_run: string;
  status: "healthy" | "stale" | "failed";
  severity: Severity;
}

/** Complete security overview */
export interface SecurityOverview {
  // Summary counts
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;

  // System status
  system_status: SystemStatus;
  last_scan_time: string | null;
  scan_status: string;

  // Provider status
  healthy_providers: number;
  degraded_providers: number;
  failed_providers: number;

  // Recent activity
  recent_alerts: SecurityAlert[];
  recent_findings: ScanFinding[];
  cve_risks: CVERisk[];
  provider_issues: ProviderHealthIssue[];
  timer_anomalies: TimerAnomaly[];

  // Metadata
  generated_at: string;
}

/** System health snapshot */
export interface SystemHealth {
  state: string;
  health_status: string;
  health_issues: string[];
  last_scan: string | null;
  scan_result: string;
}

/** Acknowledge alert response */
export interface AcknowledgeResponse {
  success: boolean;
  alert_id: string;
  timestamp: string;
}

/** Tab types for security panel */
export type SecurityTab = "overview" | "alerts" | "findings" | "health";

/** Severity filter options */
export type SeverityFilter = "all" | Severity;

/** Alert category filter options */
export type CategoryFilter = "all" | AlertCategory;
