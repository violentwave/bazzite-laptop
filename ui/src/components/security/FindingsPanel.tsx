"use client";

import { ScanFinding } from "@/types/security";
import { formatTimestamp } from "@/hooks/useSecurity";

interface FindingsPanelProps {
  findings: ScanFinding[];
  isLoading: boolean;
}

export function FindingsPanel({ findings, isLoading }: FindingsPanelProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3
              className="text-lg font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              Scan Findings
            </h3>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Recent security scan results
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="text-sm px-3 py-1 rounded-full"
              style={{
                background: "var(--base-03)",
                color: "var(--text-secondary)",
              }}
            >
              {findings.length} finding{findings.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Findings List */}
      {findings.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}

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

function FindingCard({ finding }: { finding: ScanFinding }) {
  const statusConfig: Record<
    string,
    { color: string; bgColor: string; icon: React.ReactNode }
  > = {
    clean: {
      color: "var(--success)",
      bgColor: "rgba(34, 197, 94, 0.1)",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ),
    },
    infected: {
      color: "var(--danger)",
      bgColor: "rgba(239, 68, 68, 0.1)",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      ),
    },
    error: {
      color: "var(--warning)",
      bgColor: "rgba(245, 158, 11, 0.1)",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      ),
    },
    pending: {
      color: "var(--accent-primary)",
      bgColor: "rgba(99, 102, 241, 0.1)",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
    },
  };

  const config = statusConfig[finding.status] || statusConfig.pending;

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="flex items-start gap-4">
        {/* Status Icon */}
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
          style={{
            background: config.bgColor,
            color: config.color,
          }}
        >
          {config.icon}
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <h4
                className="font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {finding.scan_type} Scan
              </h4>
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  background: config.bgColor,
                  color: config.color,
                }}
              >
                {finding.status.charAt(0).toUpperCase() +
                  finding.status.slice(1)}
              </span>
            </div>
            <span
              className="text-xs"
              style={{ color: "var(--text-tertiary)" }}
            >
              {formatTimestamp(finding.timestamp)}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <StatItem
              label="Files Scanned"
              value={finding.files_scanned.toString()}
            />
            <StatItem
              label="Threats Found"
              value={finding.threats_found.toString()}
              highlight={finding.threats_found > 0}
            />
            <StatItem
              label="Scan ID"
              value={finding.id.slice(0, 8) + "..."}
            />
          </div>

          {finding.details && (
            <div
              className="mt-3 p-3 rounded-lg text-sm font-mono"
              style={{
                background: "var(--base-01)",
                color: "var(--text-secondary)",
              }}
            >
              {finding.details}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatItem({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <div className="text-xs mb-1" style={{ color: "var(--text-tertiary)" }}>
        {label}
      </div>
      <div
        className="font-mono text-sm"
        style={{
          color: highlight ? "var(--danger)" : "var(--text-primary)",
          fontWeight: highlight ? 600 : 400,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div
      className="p-12 rounded-xl border text-center"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div
        className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
        style={{ background: "var(--base-03)" }}
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-tertiary)"
          strokeWidth="2"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      </div>
      <h3
        className="text-lg font-medium mb-2"
        style={{ color: "var(--text-primary)" }}
      >
        No Findings Yet
      </h3>
      <p style={{ color: "var(--text-secondary)" }}>
        Scan results will appear here after security scans complete.
      </p>
    </div>
  );
}
