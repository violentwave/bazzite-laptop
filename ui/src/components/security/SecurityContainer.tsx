"use client";

import { useState } from "react";
import { useSecurity } from "@/hooks/useSecurity";
import { SecurityTab } from "@/types/security";
import { callMCPTool } from "@/lib/mcp-client";
import { SecurityOverview as SecurityOverviewPanel } from "./SecurityOverview";
import { AlertFeed } from "./AlertFeed";
import { FindingsPanel } from "./FindingsPanel";
import { HealthCluster } from "./HealthCluster";
import { SecurityActionsPanel } from "./SecurityActionsPanel";

function getErrorSeverity(errorCode: string | null): 'error' | 'warning' | 'info' {
  if (!errorCode) return 'error';
  if (errorCode === 'alerts_file_unavailable' || errorCode === 'findings_unavailable') return 'warning';
  if (errorCode === 'connection_failed') return 'error';
  return 'warning';
}

function ErrorState({
  error,
  errorCode,
  operatorAction,
  partialData,
  missingSources,
  onRetry,
}: {
  error: string;
  errorCode: string | null;
  operatorAction: string | null;
  partialData: boolean;
  missingSources: string[];
  onRetry: () => void;
}) {
  const severity = getErrorSeverity(errorCode);

  const colors = {
    error: {
      border: 'var(--danger)',
      bg: 'rgba(239, 68, 68, 0.1)',
      icon: 'var(--danger)',
    },
    warning: {
      border: 'var(--warning)',
      bg: 'rgba(245, 158, 11, 0.1)',
      icon: 'var(--warning)',
    },
    info: {
      border: 'var(--info)',
      bg: 'rgba(59, 130, 246, 0.1)',
      icon: 'var(--info)',
    },
  };

  const c = colors[severity];

  return (
    <div className="h-full flex items-center justify-center p-6">
      <div
        className="max-w-md w-full p-6 rounded-xl border"
        style={{
          background: partialData ? 'var(--base-02)' : c.bg,
          borderColor: partialData ? 'var(--warning)' : c.border,
        }}
      >
        <div className="flex items-center gap-3 mb-4">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke={partialData ? 'var(--warning)' : c.icon}
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <h3 className="font-medium" style={{ color: "var(--text-primary)" }}>
            {partialData ? 'Partial Security Data' : 'Security Data Unavailable'}
          </h3>
        </div>

        <p className="mb-2" style={{ color: "var(--text-secondary)" }}>
          {error}
        </p>

        {partialData && missingSources.length > 0 && (
          <div className="mb-4">
            <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
              Unavailable sources: {missingSources.join(', ')}
            </p>
          </div>
        )}

        {operatorAction && (
          <div
            className="mb-4 p-3 rounded-lg text-sm"
            style={{
              background: "var(--base-01)",
              color: "var(--text-secondary)",
            }}
          >
            <strong>Action needed:</strong> {operatorAction}
          </div>
        )}

        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: "var(--accent-primary)",
            color: "white",
          }}
        >
          Retry
        </button>
      </div>
    </div>
  );
}

export function SecurityContainer() {
  const [activeTab, setActiveTab] = useState<SecurityTab>("overview");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const {
    overview,
    alerts,
    findings,
    providerIssues,
    isLoading,
    error,
    errorCode,
    operatorAction,
    partialData,
    missingSources,
    refresh,
    acknowledgeAlert,
    lastRefresh,
  } = useSecurity();

  // Check if we have data despite errors
  const hasData = overview || alerts.length > 0 || findings.length > 0;

  const runQuickScan = async () => {
    try {
      const result = (await callMCPTool("security.run_scan", {
        scan_type: "quick",
      })) as { message?: string };
      setActionMessage(result?.message || "Quick scan requested.");
      await refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to trigger quick scan";
      setActionMessage(`Quick scan failed: ${message}`);
    }
  };

  const runHealthCheck = async () => {
    try {
      const result = (await callMCPTool("security.run_health")) as {
        message?: string;
        error?: string;
      };
      if (result?.error) {
        setActionMessage(`Health check failed: ${result.error}`);
      } else {
        setActionMessage(result?.message || "Health snapshot requested.");
      }
      await refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to trigger health check";
      setActionMessage(`Health check failed: ${message}`);
    }
  };

  if (isLoading && !hasData) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div
            className="w-12 h-12 rounded-full border-2 animate-spin mx-auto mb-4"
            style={{
              borderTopColor: "transparent",
              borderRightColor: "var(--base-04)",
              borderBottomColor: "var(--base-04)",
              borderLeftColor: "var(--base-04)",
            }}
          />
          <p style={{ color: "var(--text-secondary)" }}>
            Loading security data...
          </p>
        </div>
      </div>
    );
  }

  // Full error state - no data at all
  if (error && !hasData) {
    return (
      <ErrorState
        error={error}
        errorCode={errorCode}
        operatorAction={operatorAction}
        partialData={partialData}
        missingSources={missingSources}
        onRetry={refresh}
      />
    );
  }

  return (
    <div className="h-full flex">
      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Tab Navigation */}
        <div
          className="flex items-center gap-1 px-4 py-2 border-b"
          style={{
            borderColor: "var(--base-04)",
            background: "var(--base-01)",
          }}
        >
          <TabButton
            active={activeTab === "overview"}
            onClick={() => setActiveTab("overview")}
            icon={<OverviewIcon />}
            label="Overview"
          />
          <TabButton
            active={activeTab === "alerts"}
            onClick={() => setActiveTab("alerts")}
            icon={<AlertIcon />}
            label="Alerts"
            badge={overview?.critical_count || 0}
            badgeColor="var(--danger)"
          />
          <TabButton
            active={activeTab === "findings"}
            onClick={() => setActiveTab("findings")}
            icon={<ScanIcon />}
            label="Findings"
          />
          <TabButton
            active={activeTab === "health"}
            onClick={() => setActiveTab("health")}
            icon={<HealthIcon />}
            label="Health"
          />
          <div className="flex-1" />
          <button
            onClick={refresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors disabled:opacity-50"
            style={{ color: "var(--text-secondary)" }}
            title="Refresh"
          >
            <RefreshIcon spinning={isLoading} />
            <span className="hidden sm:inline">
              {lastRefresh
                ? `Updated ${lastRefresh.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}`
                : "Refresh"}
            </span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === "overview" && overview && (
            <SecurityOverviewPanel data={overview} onRefresh={refresh} />
          )}
          {activeTab === "alerts" && (
            <AlertFeed
              alerts={alerts}
              onAcknowledge={acknowledgeAlert}
              isLoading={isLoading}
            />
          )}
          {activeTab === "findings" && (
            <FindingsPanel findings={findings} isLoading={isLoading} />
          )}
          {activeTab === "health" && (
            <HealthCluster
              providerIssues={providerIssues}
              overview={overview}
              isLoading={isLoading}
            />
          )}
        </div>
      </div>

      {/* Right Sidebar - Actions */}
      <div
        className="w-80 border-l overflow-auto hidden xl:block"
        style={{
          borderColor: "var(--base-04)",
          background: "var(--base-01)",
        }}
      >
        <SecurityActionsPanel
          overview={overview}
          onRefresh={refresh}
          onRunQuickScan={runQuickScan}
          onRunHealthCheck={runHealthCheck}
          actionMessage={actionMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: number;
  badgeColor?: string;
}

function TabButton({ active, onClick, icon, label, badge, badgeColor }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors relative"
      style={{
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
        background: active ? "var(--base-03)" : "transparent",
      }}
    >
      {icon}
      <span>{label}</span>
      {badge !== undefined && badge > 0 && (
        <span
          className="px-1.5 py-0.5 rounded-full text-xs font-bold"
          style={{
            background: badgeColor || "var(--danger)",
            color: "white",
          }}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

function RefreshIcon({ spinning }: { spinning?: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={spinning ? "animate-spin" : ""}
    >
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 12" />
      <path d="M3 3v9h9" />
    </svg>
  );
}

function OverviewIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect width="7" height="9" x="3" y="3" rx="1" />
      <rect width="7" height="5" x="14" y="3" rx="1" />
      <rect width="7" height="9" x="14" y="12" rx="1" />
      <rect width="7" height="5" x="3" y="16" rx="1" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

function ScanIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 7V5a2 2 0 0 1 2-2h2" />
      <path d="M17 3h2a2 2 0 0 1 2 2v2" />
      <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
      <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
    </svg>
  );
}

function HealthIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}
