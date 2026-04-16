"use client";

import { useCallback, useEffect, useState } from "react";
import { callMCPTool } from "@/lib/mcp-client";
import {
  AutopilotAuditEvent,
  AutopilotEvidenceBundle,
  AutopilotFinding,
  AutopilotIncident,
  AutopilotOverview,
  AutopilotPolicyStatus,
  AutopilotQueueItem,
} from "@/types/security-autopilot";

interface ErrorEnvelope {
  success?: boolean;
  error?: string;
  error_code?: string;
  operator_action?: string;
}

interface UseSecurityAutopilotReturn {
  overview: AutopilotOverview | null;
  findings: AutopilotFinding[];
  incidents: AutopilotIncident[];
  evidence: AutopilotEvidenceBundle[];
  auditEvents: AutopilotAuditEvent[];
  policy: AutopilotPolicyStatus | null;
  remediationQueue: AutopilotQueueItem[];
  isLoading: boolean;
  isPartial: boolean;
  error: string | null;
  errorCode: string | null;
  operatorAction: string | null;
  missingSources: string[];
  lastRefresh: Date | null;
  refresh: () => Promise<void>;
}

function parseError(name: string, payload: unknown): ErrorEnvelope | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const typed = payload as ErrorEnvelope;
  if (typed.success === false) {
    return {
      success: false,
      error: typed.error || `${name} unavailable`,
      error_code: typed.error_code || "autopilot_tool_error",
      operator_action:
        typed.operator_action || "Review MCP bridge logs for tool execution errors",
    };
  }

  return null;
}

export function useSecurityAutopilot(): UseSecurityAutopilotReturn {
  const [overview, setOverview] = useState<AutopilotOverview | null>(null);
  const [findings, setFindings] = useState<AutopilotFinding[]>([]);
  const [incidents, setIncidents] = useState<AutopilotIncident[]>([]);
  const [evidence, setEvidence] = useState<AutopilotEvidenceBundle[]>([]);
  const [auditEvents, setAuditEvents] = useState<AutopilotAuditEvent[]>([]);
  const [policy, setPolicy] = useState<AutopilotPolicyStatus | null>(null);
  const [remediationQueue, setRemediationQueue] = useState<AutopilotQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPartial, setIsPartial] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [operatorAction, setOperatorAction] = useState<string | null>(null);
  const [missingSources, setMissingSources] = useState<string[]>([]);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setErrorCode(null);
    setOperatorAction(null);
    setMissingSources([]);
    setIsPartial(false);

    const missing: string[] = [];
    let firstError: ErrorEnvelope | null = null;

    const captureError = (toolName: string, value: unknown) => {
      const parsed = parseError(toolName, value);
      if (parsed) {
        if (!firstError) {
          firstError = parsed;
        }
        missing.push(toolName);
      }
    };

    try {
      const [
        overviewRaw,
        findingsRaw,
        incidentsRaw,
        evidenceRaw,
        auditRaw,
        policyRaw,
        remediationRaw,
      ] = await Promise.all([
        callMCPTool("security.autopilot_overview"),
        callMCPTool("security.autopilot_findings", { limit: 50 }),
        callMCPTool("security.autopilot_incidents", { limit: 25 }),
        callMCPTool("security.autopilot_evidence", { limit: 25 }),
        callMCPTool("security.autopilot_audit", { limit: 50 }),
        callMCPTool("security.autopilot_policy"),
        callMCPTool("security.autopilot_remediation_queue", { limit: 25 }),
      ]);

      captureError("overview", overviewRaw);
      captureError("findings", findingsRaw);
      captureError("incidents", incidentsRaw);
      captureError("evidence", evidenceRaw);
      captureError("audit", auditRaw);
      captureError("policy", policyRaw);
      captureError("remediation", remediationRaw);

      if (
        overviewRaw &&
        typeof overviewRaw === "object" &&
        (overviewRaw as { success?: boolean }).success !== false
      ) {
        setOverview(((overviewRaw as { data?: AutopilotOverview }).data || null) as AutopilotOverview | null);
      } else {
        setOverview(null);
      }

      setFindings(((findingsRaw as { findings?: AutopilotFinding[] })?.findings || []) as AutopilotFinding[]);
      setIncidents(((incidentsRaw as { incidents?: AutopilotIncident[] })?.incidents || []) as AutopilotIncident[]);
      setEvidence(((evidenceRaw as { bundles?: AutopilotEvidenceBundle[] })?.bundles || []) as AutopilotEvidenceBundle[]);
      setAuditEvents(((auditRaw as { events?: AutopilotAuditEvent[] })?.events || []) as AutopilotAuditEvent[]);
      setPolicy(((policyRaw as { policy?: AutopilotPolicyStatus })?.policy || null) as AutopilotPolicyStatus | null);
      setRemediationQueue(((remediationRaw as { queue?: AutopilotQueueItem[] })?.queue || []) as AutopilotQueueItem[]);

      if (missing.length > 0) {
        setIsPartial(true);
        setMissingSources(missing);
      }
      const resolvedError = firstError as ErrorEnvelope | null;
      if (resolvedError) {
        setError(resolvedError.error || "Security autopilot data unavailable");
        setErrorCode(resolvedError.error_code || "autopilot_tool_error");
        setOperatorAction(resolvedError.operator_action || null);
      }

      setLastRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(`Unable to load security autopilot tools: ${message}`);
      setErrorCode("autopilot_connection_failed");
      setOperatorAction("Ensure MCP bridge is running and security.autopilot_* tools are available");
      setOverview(null);
      setFindings([]);
      setIncidents([]);
      setEvidence([]);
      setAuditEvents([]);
      setPolicy(null);
      setRemediationQueue([]);
      setMissingSources([
        "overview",
        "findings",
        "incidents",
        "evidence",
        "audit",
        "policy",
        "remediation",
      ]);
      setIsPartial(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = setInterval(() => {
      void refresh();
    }, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  return {
    overview,
    findings,
    incidents,
    evidence,
    auditEvents,
    policy,
    remediationQueue,
    isLoading,
    isPartial,
    error,
    errorCode,
    operatorAction,
    missingSources,
    lastRefresh,
    refresh,
  };
}
