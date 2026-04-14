"use client";

import { ProviderHealthIssue, SecurityOverview } from "@/types/security";
import { formatTimestamp } from "@/hooks/useSecurity";

interface HealthClusterProps {
  providerIssues: ProviderHealthIssue[];
  overview: SecurityOverview | null;
  isLoading: boolean;
}

export function HealthCluster({
  providerIssues,
  overview,
  isLoading,
}: HealthClusterProps) {
  return (
    <div className="space-y-6">
      {/* Provider Health Summary */}
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="text-lg font-medium mb-4"
          style={{ color: "var(--text-primary)" }}
        >
          Provider Health Status
        </h3>

        {overview && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <HealthCard
              count={overview.healthy_providers}
              label="Healthy"
              color="var(--success)"
              description="Fully operational"
            />
            <HealthCard
              count={overview.degraded_providers}
              label="Degraded"
              color="var(--warning)"
              description="Performance issues"
            />
            <HealthCard
              count={overview.failed_providers}
              label="Failed"
              color="var(--danger)"
              description="Auth or connection errors"
            />
          </div>
        )}

        {/* Provider Issues List */}
        {providerIssues.length > 0 ? (
          <div className="space-y-3">
            <h4
              className="text-sm font-medium mb-3"
              style={{ color: "var(--text-secondary)" }}
            >
              Active Issues
            </h4>
            {providerIssues.map((issue, index) => (
              <ProviderIssueCard key={index} issue={issue} />
            ))}
          </div>
        ) : (
          <div
            className="p-4 rounded-lg text-center"
            style={{
              background: "var(--base-01)",
              border: "1px dashed var(--base-04)",
            }}
          >
            <p style={{ color: "var(--text-secondary)" }}>
              All providers operating normally
            </p>
          </div>
        )}
      </div>

      {/* System Health */}
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="text-lg font-medium mb-4"
          style={{ color: "var(--text-primary)" }}
        >
          System Health
        </h3>

        <div className="space-y-4">
          {/* Scan Status */}
          <HealthMetricRow
            label="Last Security Scan"
            value={
              overview?.last_scan_time
                ? formatTimestamp(overview.last_scan_time)
                : "Never"
            }
            status={overview?.scan_status === "clean" ? "success" : "neutral"}
          />

          {/* System Status */}
          <HealthMetricRow
            label="Overall Status"
            value={
              overview?.system_status === "secure"
                ? "Secure"
                : overview?.system_status === "warning"
                ? "Warning"
                : overview?.system_status === "critical"
                ? "Critical"
                : "Unknown"
            }
            status={
              overview?.system_status === "secure"
                ? "success"
                : overview?.system_status === "warning"
                ? "warning"
                : "error"
            }
          />

          {/* Provider Summary */}
          <HealthMetricRow
            label="Total Providers"
            value={`${
              (overview?.healthy_providers || 0) +
              (overview?.degraded_providers || 0) +
              (overview?.failed_providers || 0)
            } configured`}
            status="neutral"
          />
        </div>
      </div>

      {isLoading && (
        <div className="text-center py-4">
          <div
            className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin mx-auto"
            style={{
              borderColor: "var(--base-04)",
              borderTopColor: "var(--accent-primary)",
            }}
          />
        </div>
      )}
    </div>
  );
}

function HealthCard({
  count,
  label,
  color,
  description,
}: {
  count: number;
  label: string;
  color: string;
  description: string;
}) {
  return (
    <div
      className="p-4 rounded-lg border text-center"
      style={{
        background: "var(--base-01)",
        borderColor: count > 0 ? `${color}40` : "var(--base-04)",
      }}
    >
      <div
        className="text-3xl font-bold mb-1"
        style={{ color: count > 0 ? color : "var(--text-tertiary)" }}
      >
        {count}
      </div>
      <div
        className="text-sm font-medium mb-1"
        style={{ color: count > 0 ? color : "var(--text-secondary)" }}
      >
        {label}
      </div>
      <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
        {description}
      </div>
    </div>
  );
}

function ProviderIssueCard({ issue }: { issue: ProviderHealthIssue }) {
  const issueTypeConfig: Record<string, { label: string; color: string }> = {
    auth_failed: { label: "Auth Failed", color: "var(--danger)" },
    timeout: { label: "Timeout", color: "var(--warning)" },
    error: { label: "Error", color: "var(--danger)" },
    degraded: { label: "Degraded", color: "var(--warning)" },
  };

  const config = issueTypeConfig[issue.issue_type] || {
    label: issue.issue_type,
    color: "var(--text-secondary)",
  };

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-01)",
        borderColor: issue.auth_broken
          ? "var(--danger)"
          : "var(--base-04)",
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-2 h-2 rounded-full"
            style={{
              background: issue.auth_broken
                ? "var(--danger)"
                : "var(--warning)",
            }}
          />
          <div>
            <div className="flex items-center gap-2">
              <h4
                className="font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {issue.provider}
              </h4>
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  background: `${config.color}20`,
                  color: config.color,
                }}
              >
                {config.label}
              </span>
              {issue.auth_broken && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    background: "var(--danger)",
                    color: "white",
                  }}
                >
                  Auth Broken
                </span>
              )}
            </div>
            <p
              className="text-sm mt-1"
              style={{ color: "var(--text-secondary)" }}
            >
              {issue.description}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div
            className="text-xs"
            style={{ color: "var(--text-tertiary)" }}
          >
            {formatTimestamp(issue.timestamp)}
          </div>
          <div
            className="text-xs mt-1"
            style={{ color: "var(--text-tertiary)" }}
          >
            {issue.consecutive_failures} consecutive failures
          </div>
        </div>
      </div>
    </div>
  );
}

function HealthMetricRow({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: "success" | "warning" | "error" | "neutral";
}) {
  const statusColors = {
    success: "var(--success)",
    warning: "var(--warning)",
    error: "var(--danger)",
    neutral: "var(--text-secondary)",
  };

  return (
    <div className="flex items-center justify-between py-2">
      <span style={{ color: "var(--text-secondary)" }}>{label}</span>
      <div className="flex items-center gap-2">
        {status !== "neutral" && (
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: statusColors[status] }}
          />
        )}
        <span
          className="font-medium"
          style={{ color: statusColors[status] }}
        >
          {value}
        </span>
      </div>
    </div>
  );
}
