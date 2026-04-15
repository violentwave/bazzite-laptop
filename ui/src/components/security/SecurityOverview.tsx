"use client";

import { SecurityOverview as SecurityOverviewType } from "@/types/security";
import { getSeverityColor, formatTimestamp } from "@/hooks/useSecurity";

interface SecurityOverviewProps {
  data: SecurityOverviewType;
  onRefresh: () => void;
}

export function SecurityOverview({ data }: SecurityOverviewProps) {
  const statusColors: Record<string, string> = {
    secure: "var(--success)",
    warning: "var(--warning)",
    critical: "var(--danger)",
    unknown: "var(--text-tertiary)",
  };

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div
              className="w-16 h-16 rounded-xl flex items-center justify-center"
              style={{
                background:
                  data.system_status === "secure"
                    ? "rgba(34, 197, 94, 0.1)"
                    : data.system_status === "warning"
                    ? "rgba(245, 158, 11, 0.1)"
                    : "rgba(239, 68, 68, 0.1)",
              }}
            >
              <SecurityStatusIcon status={data.system_status} />
            </div>
            <div>
              <h2
                className="text-2xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                System{" "}
                {data.system_status === "secure"
                  ? "Secure"
                  : data.system_status === "warning"
                  ? "Warning"
                  : "Critical"}
              </h2>
              <p style={{ color: "var(--text-secondary)" }}>
                Last scan:{" "}
                {data.last_scan_time
                  ? formatTimestamp(data.last_scan_time)
                  : "Never"}
              </p>
            </div>
          </div>
          <div
            className="px-4 py-2 rounded-full text-sm font-medium"
            style={{
              background: `${statusColors[data.system_status]}20`,
              color: statusColors[data.system_status],
              border: `1px solid ${statusColors[data.system_status]}40`,
            }}
          >
            {data.scan_status === "clean" ? "No Threats" : data.scan_status}
          </div>
        </div>

        {/* Severity Counts */}
        <div className="grid grid-cols-4 gap-4 mt-6">
          <SeverityCountCard
            count={data.critical_count}
            label="Critical"
            color="var(--danger)"
          />
          <SeverityCountCard
            count={data.high_count}
            label="High"
            color="var(--warning)"
          />
          <SeverityCountCard
            count={data.medium_count}
            label="Medium"
            color="var(--accent-primary)"
          />
          <SeverityCountCard
            count={data.low_count}
            label="Low"
            color="var(--text-secondary)"
          />
        </div>
      </div>

      {/* Provider Health */}
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
          Provider Health
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <ProviderStatusCard
            count={data.healthy_providers}
            label="Healthy"
            color="var(--success)"
          />
          <ProviderStatusCard
            count={data.degraded_providers}
            label="Degraded"
            color="var(--warning)"
          />
          <ProviderStatusCard
            count={data.failed_providers}
            label="Failed"
            color="var(--danger)"
          />
        </div>
      </div>

      {/* Recent Alerts */}
      {data.recent_alerts?.length > 0 && (
        <div
          className="rounded-xl border overflow-hidden"
          style={{
            background: "var(--base-02)",
            borderColor: "var(--base-04)",
          }}
        >
          <div
            className="px-6 py-4 border-b"
            style={{ borderColor: "var(--base-04)" }}
          >
            <h3
              className="text-lg font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              Recent Alerts
            </h3>
          </div>
          <div className="divide-y" style={{ borderColor: "var(--base-04)" }}>
            {data.recent_alerts?.slice(0, 5).map((alert) => (
              <div
                key={alert.id}
                className="px-6 py-4 flex items-start gap-4 hover:bg-base-03 transition-colors"
              >
                <div
                  className="w-2 h-2 rounded-full mt-2"
                  style={{ background: getSeverityColor(alert.severity) }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4
                      className="font-medium truncate"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {alert.title}
                    </h4>
                    <span
                      className="text-xs shrink-0"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {formatTimestamp(alert.timestamp)}
                    </span>
                  </div>
                  <p
                    className="text-sm truncate"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {alert.description}
                  </p>
                </div>
                <span
                  className="text-xs px-2 py-1 rounded-full shrink-0"
                  style={{
                    background: `${getSeverityColor(alert.severity)}20`,
                    color: getSeverityColor(alert.severity),
                  }}
                >
                  {alert.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SeverityCountCard({
  count,
  label,
  color,
}: {
  count: number;
  label: string;
  color: string;
}) {
  return (
    <div
      className="p-4 rounded-lg border text-center"
      style={{
        background: "var(--base-01)",
        borderColor: "var(--base-04)",
      }}
    >
      <div
        className="text-3xl font-bold mb-1"
        style={{ color: count > 0 ? color : "var(--text-tertiary)" }}
      >
        {count}
      </div>
      <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {label}
      </div>
    </div>
  );
}

function ProviderStatusCard({
  count,
  label,
  color,
}: {
  count: number;
  label: string;
  color: string;
}) {
  return (
    <div
      className="p-4 rounded-lg border text-center"
      style={{
        background: "var(--base-01)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="text-2xl font-bold mb-1" style={{ color }}>
        {count}
      </div>
      <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {label}
      </div>
    </div>
  );
}

function SecurityStatusIcon({ status }: { status: string }) {
  const colors: Record<string, string> = {
    secure: "var(--success)",
    warning: "var(--warning)",
    critical: "var(--danger)",
    unknown: "var(--text-tertiary)",
  };

  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke={colors[status] || colors.unknown}
      strokeWidth="2"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      {status === "secure" && <polyline points="9 12 12 15 16 10" />}
      {status === "warning" && (
        <>
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </>
      )}
      {status === "critical" && (
        <>
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </>
      )}
    </svg>
  );
}
