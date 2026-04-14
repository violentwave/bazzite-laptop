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

interface UseSecurityReturn {
  overview: SecurityOverview | null;
  alerts: SecurityAlert[];
  findings: ScanFinding[];
  providerIssues: ProviderHealthIssue[];
  systemHealth: SystemHealth | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<AcknowledgeResponse>;
  lastRefresh: Date | null;
}

export function useSecurity(): UseSecurityReturn {
  const [overview, setOverview] = useState<SecurityOverview | null>(null);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [findings, setFindings] = useState<ScanFinding[]>([]);
  const [providerIssues, setProviderIssues] = useState<ProviderHealthIssue[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch overview
      const overviewData = await callMCPTool("security.ops_overview");
      setOverview((overviewData || null) as SecurityOverview | null);

      // Fetch alerts
      const alertsData = await callMCPTool("security.ops_alerts", { limit: 50 });
      setAlerts(Array.isArray(alertsData) ? (alertsData as SecurityAlert[]) : []);

      // Fetch findings
      const findingsData = await callMCPTool("security.ops_findings", { limit: 20 });
      setFindings(Array.isArray(findingsData) ? (findingsData as ScanFinding[]) : []);

      // Fetch provider health issues
      const issuesData = await callMCPTool("security.ops_provider_health");
      setProviderIssues(Array.isArray(issuesData) ? (issuesData as ProviderHealthIssue[]) : []);

      // Fetch system health
      const healthData = await callMCPTool("security.status");
      setSystemHealth((healthData || null) as SystemHealth | null);

      setLastRefresh(new Date());
    } catch (err) {
      setError(
        err instanceof Error
          ? `Security data load failed: ${err.message}`
          : "Security data load failed"
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    await fetchAll();
  }, [fetchAll]);

  const acknowledgeAlert = useCallback(async (alertId: string): Promise<AcknowledgeResponse> => {
    const result = await callMCPTool("security.ops_acknowledge", { alert_id: alertId });
    
    // Refresh alerts after acknowledging
    await fetchAll();
    
    return result as AcknowledgeResponse;
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
