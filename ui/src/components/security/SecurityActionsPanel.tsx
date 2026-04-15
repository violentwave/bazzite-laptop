"use client";

import { SecurityOverview } from "@/types/security";
import { getSeverityColor } from "@/hooks/useSecurity";

interface SecurityActionsPanelProps {
  overview: SecurityOverview | null;
  onRefresh: () => void;
  onRunQuickScan: () => Promise<void>;
  onRunHealthCheck: () => Promise<void>;
  actionMessage: string | null;
  isLoading: boolean;
}

export function SecurityActionsPanel({
  overview,
  onRefresh,
  onRunQuickScan,
  onRunHealthCheck,
  actionMessage,
  isLoading,
}: SecurityActionsPanelProps) {
  return (
    <div className="p-4 space-y-6">
      {/* Quick Actions */}
      <div>
        <h3
          className="text-sm font-medium mb-3 uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          Quick Actions
        </h3>
        <div className="space-y-2">
          <ActionButton
            icon={<ScanIcon />}
            label="Run Quick Scan"
            onClick={() => {
              void onRunQuickScan();
            }}
            disabled={isLoading}
          />
          <ActionButton
            icon={<HealthIcon />}
            label="System Health Check"
            onClick={() => {
              void onRunHealthCheck();
            }}
            disabled={isLoading}
          />
          <ActionButton
            icon={<RefreshIcon />}
            label="Refresh Data"
            onClick={onRefresh}
            disabled={isLoading}
          />
        </div>
      </div>

      {/* Summary Stats */}
      {overview && (
        <div>
          <h3
            className="text-sm font-medium mb-3 uppercase tracking-wider"
            style={{ color: "var(--text-tertiary)" }}
          >
            Alert Summary
          </h3>
          <div className="space-y-2">
            <SummaryRow
              label="Critical"
              count={overview.critical_count}
              color={getSeverityColor("critical")}
            />
            <SummaryRow
              label="High"
              count={overview.high_count}
              color={getSeverityColor("high")}
            />
            <SummaryRow
              label="Medium"
              count={overview.medium_count}
              color={getSeverityColor("medium")}
            />
            <SummaryRow
              label="Low"
              count={overview.low_count}
              color={getSeverityColor("low")}
            />
          </div>
        </div>
      )}

      {/* Provider Status */}
      {overview && (
        <div>
          <h3
            className="text-sm font-medium mb-3 uppercase tracking-wider"
            style={{ color: "var(--text-tertiary)" }}
          >
            Providers
          </h3>
          <div className="space-y-2">
            <SummaryRow
              label="Healthy"
              count={overview.healthy_providers}
              color="var(--success)"
            />
            <SummaryRow
              label="Degraded"
              count={overview.degraded_providers}
              color="var(--warning)"
            />
            <SummaryRow
              label="Failed"
              count={overview.failed_providers}
              color="var(--danger)"
            />
          </div>
        </div>
      )}

      {/* Links */}
      <div>
        <h3
          className="text-sm font-medium mb-3 uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          Resources
        </h3>
        <div className="space-y-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          <p>Use Alerts tab for active incidents and acknowledgement.</p>
          <p>Use Findings tab for scan output and threat details.</p>
          <p>Use Providers panel for API key and routing changes.</p>
        </div>
      </div>

      {/* Footer Info */}
      <div
        className="pt-4 border-t"
        style={{ borderColor: "var(--base-04)" }}
      >
        {actionMessage && (
          <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>
            {actionMessage}
          </p>
        )}
        <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Last updated: {overview?.generated_at
            ? new Date(overview.generated_at).toLocaleTimeString()
            : "Never"}
        </p>
        <p
          className="text-xs mt-1"
          style={{ color: "var(--text-tertiary)" }}
        >
          Auto-refreshes every 30 seconds
        </p>
      </div>
    </div>
  );
}

function ActionButton({
  icon,
  label,
  onClick,
  disabled,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  badge?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 hover:bg-base-03"
      style={{
        background: "var(--base-02)",
        color: badge ? "var(--text-tertiary)" : "var(--text-primary)",
      }}
    >
      <span style={{ color: "var(--text-secondary)" }}>{icon}</span>
      {label}
      {badge && (
        <span
          className="text-[10px] px-1.5 py-0.5 rounded ml-auto"
          style={{ background: "var(--base-03)", color: "var(--text-tertiary)" }}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

function SummaryRow({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {label}
      </span>
      <span
        className="text-sm font-bold"
        style={{ color: count > 0 ? color : "var(--text-tertiary)" }}
      >
        {count}
      </span>
    </div>
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

function RefreshIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 12" />
      <path d="M3 3v9h9" />
    </svg>
  );
}
