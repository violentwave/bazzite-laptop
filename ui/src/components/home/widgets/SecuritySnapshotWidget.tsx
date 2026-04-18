"use client";

import { useMemo } from "react";
import { WidgetContainer } from "./WidgetContainer";
import { useSecurity } from "@/hooks/useSecurity";
import { summarizeSecurityWidget } from "@/lib/home-dashboard";
import { useShell } from "@/components/shell/ShellContext";

type SecuritySnapshotWidgetProps = {
  onRemove?: () => void;
};

export function SecuritySnapshotWidget({ onRemove }: SecuritySnapshotWidgetProps = {}) {
  const { setActivePanel } = useShell();
  const {
    overview,
    alerts,
    findings,
    systemHealth,
    isLoading,
    error,
  } = useSecurity();

  const securitySummary = useMemo(
    () => summarizeSecurityWidget(overview, alerts, findings, systemHealth),
    [overview, alerts, findings, systemHealth]
  );

  if (isLoading) {
    return (
      <WidgetContainer
        title="Security Snapshot"
        subtitle="Safety summary and alert count"
        onRemove={onRemove}
      >
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </WidgetContainer>
    );
  }

  return (
    <WidgetContainer 
      title="Security Snapshot" 
      subtitle="Safety summary and alert count"
      onConfigure={() => setActivePanel("security")}
      onRemove={onRemove}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-tertiary">System Health</span>
          <span
            className="px-2 py-1 rounded text-xs"
            style={{
              border: "1px solid var(--base-4)",
              background: "var(--base-1)",
              color:
                securitySummary.status === "critical" || securitySummary.critical > 0
                  ? "var(--danger)"
                  : securitySummary.status === "warning" || securitySummary.alerts > 0
                    ? "var(--warning)"
                    : securitySummary.status === "healthy"
                      ? "var(--success)"
                      : "var(--text-tertiary)",
            }}
          >
            {securitySummary.status.toUpperCase()}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Critical</div>
            <div className="text-xl font-bold text-danger">{securitySummary.critical}</div>
          </div>
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">High Risk</div>
            <div className="text-xl font-bold text-warning">{securitySummary.high}</div>
          </div>
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Alerts</div>
            <div className="text-xl font-bold text-warning">{securitySummary.alerts}</div>
          </div>
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Findings</div>
            <div className="text-xl font-bold text-primary">{securitySummary.findings}</div>
          </div>
        </div>

        {error && (
          <div className="text-xs text-danger mt-2">
            Error: {error}
          </div>
        )}
      </div>
    </WidgetContainer>
  );
}
