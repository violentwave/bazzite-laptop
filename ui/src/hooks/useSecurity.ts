"use client";

import { useState, useEffect, useCallback } from "react";
import {
  SecurityOverview,
  SecurityAlert,
  ScanFinding,
  ProviderHealthIssue,
  SystemHealth,
  AcknowledgeResponse,
  Severity,
} from "@/types/security";
import { callMCPTool } from "@/lib/mcp-client";

interface OverviewResponse {
  success?: boolean;
  data?: SecurityOverview;
  partial_data?: boolean;
  missing_sources?: string[];
  operator_action?: string;
  error_code?: string;
  error?: string;
}

interface AlertsResponse {
  success?: boolean;
  alerts?: SecurityAlert[];
  count?: number;
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface FindingsResponse {
  success?: boolean;
  findings?: ScanFinding[];
  count?: number;
  logs_available?: boolean;
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface ProviderIssuesResponse {
  success?: boolean;
  issues?: ProviderHealthIssue[];
  count?: number;
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface UseSecurityReturn {
  overview: SecurityOverview | null;
  alerts: SecurityAlert[];
  findings: ScanFinding[];
  providerIssues: ProviderHealthIssue[];
  systemHealth: SystemHealth | null;
  isLoading: boolean;
  error: string | null;
  errorCode: string | null;
  operatorAction: string | null;
  partialData: boolean;
  missingSources: string[];
  refresh: () => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<AcknowledgeResponse>;
  lastRefresh: Date | null;
}

function formatSecurityError(
  response: OverviewResponse | AlertsResponse | FindingsResponse | ProviderIssuesResponse
): { message: string; code: string; action: string } {
  const code = response.error_code || 'unknown_error';
  const action = response.operator_action || 'Check MCP bridge and security service health';

  switch (code) {
    case 'overview_unavailable':
      return {
        message: response.error || 'Security overview unavailable',
        code,
        action,
      };
    case 'alerts_file_unavailable':
      return {
        message: 'Security alerts file not found',
        code,
        action: 'Check security-alert.timer is enabled and running',
      };
    case 'alerts_unavailable':
      return {
        message: response.error || 'Failed to load security alerts',
        code,
        action,
      };
    case 'findings_unavailable':
      return {
        message: response.error || 'Failed to load scan findings',
        code,
        action: 'Check ClamAV log directory permissions',
      };
    case 'provider_health_unavailable':
      return {
        message: response.error || 'Provider health data unavailable',
        code,
        action: 'Check LLM status file and provider service',
      };
    default:
      return {
        message: response.error || 'Security service error',
        code,
        action,
      };
  }
}

export function useSecurity(): UseSecurityReturn {
  const [overview, setOverview] = useState<SecurityOverview | null>(null);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [findings, setFindings] = useState<ScanFinding[]>([]);
  const [providerIssues, setProviderIssues] = useState<ProviderHealthIssue[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [operatorAction, setOperatorAction] = useState<string | null>(null);
  const [partialData, setPartialData] = useState(false);
  const [missingSources, setMissingSources] = useState<string[]>([]);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setErrorCode(null);
    setOperatorAction(null);
    setPartialData(false);
    setMissingSources([]);

    try {
      // Fetch overview
      const overviewData = await callMCPTool("security.ops_overview");
      const overviewResp = overviewData as OverviewResponse;
      let hasError = false;

      if (overviewResp.success === false) {
        const err = formatSecurityError(overviewResp);
        setError(err.message);
        setErrorCode(err.code);
        setOperatorAction(err.action);
        setOverview(null);
        hasError = true;
      } else {
        setOverview(overviewResp.data || null);
        if (overviewResp.partial_data) {
          setPartialData(true);
          setMissingSources(overviewResp.missing_sources || []);
          setOperatorAction(overviewResp.operator_action || '');
        }
      }

      // Fetch alerts
      const alertsData = await callMCPTool("security.ops_alerts", { limit: 50 });
      const alertsResp = alertsData as AlertsResponse;

      if (alertsResp.success === false) {
        if (!hasError) {
          const err = formatSecurityError(alertsResp);
          setError(err.message);
          setErrorCode(err.code);
          setOperatorAction(err.action);
          hasError = true;
        }
        setPartialData(true);
        setMissingSources(prev => [...prev, 'alerts']);
        setAlerts([]);
      } else {
        setAlerts(alertsResp.alerts || []);
      }

      // Fetch findings
      const findingsData = await callMCPTool("security.ops_findings", { limit: 20 });
      const findingsResp = findingsData as FindingsResponse;

      if (findingsResp.success === false) {
        if (!hasError) {
          const err = formatSecurityError(findingsResp);
          setError(err.message);
          setErrorCode(err.code);
          setOperatorAction(err.action);
          hasError = true;
        }
        setPartialData(true);
        setMissingSources(prev => [...prev, 'findings']);
        setFindings([]);
      } else {
        setFindings(findingsResp.findings || []);
      }

      // Fetch provider health issues
      const issuesData = await callMCPTool("security.ops_provider_health");
      const issuesResp = issuesData as ProviderIssuesResponse;

      if (issuesResp.success === false) {
        if (!hasError) {
          const err = formatSecurityError(issuesResp);
          setError(err.message);
          setErrorCode(err.code);
          setOperatorAction(err.action);
          hasError = true;
        }
        setPartialData(true);
        setMissingSources(prev => [...prev, 'provider_health']);
        setProviderIssues([]);
      } else {
        setProviderIssues(issuesResp.issues || []);
      }

      // Fetch system health
      const healthData = await callMCPTool("security.status");
      setSystemHealth((healthData || null) as SystemHealth | null);

      setLastRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Security service unavailable';
      setError(`Cannot connect to security service: ${message}`);
      setErrorCode('connection_failed');
      setOperatorAction('Ensure MCP bridge is running on port 8766');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    await fetchAll();
  }, [fetchAll]);

  const acknowledgeAlert = useCallback(async (alertId: string): Promise<AcknowledgeResponse> => {
    try {
      const result = await callMCPTool("security.ops_acknowledge", { alert_id: alertId });

      // Refresh alerts after acknowledging
      await fetchAll();

      return result as AcknowledgeResponse;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return {
        success: false,
        alert_id: '',
        timestamp: new Date().toISOString(),
        error: `Failed to acknowledge alert: ${message}`,
      } as AcknowledgeResponse;
    }
  }, [fetchAll]);

  useEffect(() => {
    fetchAll();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return {
    overview,
    alerts,
    findings,
    providerIssues,
    systemHealth,
    isLoading,
    error,
    errorCode,
    operatorAction,
    partialData,
    missingSources,
    refresh,
    acknowledgeAlert,
    lastRefresh,
  };
}

/** Hook for filtered alerts */
export function useFilteredAlerts(
  alerts: SecurityAlert[],
  severityFilter: Severity | "all",
  acknowledgedFilter: "all" | "acknowledged" | "unacknowledged"
) {
  return alerts.filter((alert) => {
    const severityMatch = severityFilter === "all" || alert.severity === severityFilter;
    const acknowledgedMatch =
      acknowledgedFilter === "all" ||
      (acknowledgedFilter === "acknowledged" && alert.acknowledged) ||
      (acknowledgedFilter === "unacknowledged" && !alert.acknowledged);
    return severityMatch && acknowledgedMatch;
  });
}

/** Get severity color for UI */
export function getSeverityColor(severity: Severity): string {
  switch (severity) {
    case "critical":
      return "var(--danger)";
    case "high":
      return "var(--warning)";
    case "medium":
      return "var(--accent-primary)";
    case "low":
      return "var(--text-secondary)";
    case "info":
      return "var(--info)";
    default:
      return "var(--text-tertiary)";
  }
}

/** Get severity label */
export function getSeverityLabel(severity: Severity): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

/** Format timestamp for display */
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  
  return date.toLocaleDateString();
}
