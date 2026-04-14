"use client";

import { useState } from "react";
import { SecurityAlert, Severity } from "@/types/security";
import {
  getSeverityColor,
  getSeverityLabel,
  formatTimestamp,
} from "@/hooks/useSecurity";
import { AcknowledgeResponse } from "@/types/security";

interface AlertFeedProps {
  alerts: SecurityAlert[];
  onAcknowledge: (alertId: string) => Promise<AcknowledgeResponse>;
  isLoading: boolean;
}

export function AlertFeed({
  alerts,
  onAcknowledge,
  isLoading,
}: AlertFeedProps) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">(
    "all"
  );
  const [acknowledgedFilter, setAcknowledgedFilter] = useState<
    "all" | "acknowledged" | "unacknowledged"
  >("unacknowledged");
  const [acknowledging, setAcknowledging] = useState<string | null>(null);

  const filteredAlerts = alerts.filter((alert) => {
    const severityMatch =
      severityFilter === "all" || alert.severity === severityFilter;
    const acknowledgedMatch =
      acknowledgedFilter === "all" ||
      (acknowledgedFilter === "acknowledged" && alert.acknowledged) ||
      (acknowledgedFilter === "unacknowledged" && !alert.acknowledged);
    return severityMatch && acknowledgedMatch;
  });

  const handleAcknowledge = async (alertId: string) => {
    setAcknowledging(alertId);
    try {
      await onAcknowledge(alertId);
    } finally {
      setAcknowledging(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div
        className="p-4 rounded-lg border flex flex-wrap items-center gap-4"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Severity:
          </span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as Severity | "all")}
            className="px-3 py-1.5 rounded-lg text-sm border bg-transparent"
            style={{
              borderColor: "var(--base-04)",
              color: "var(--text-primary)",
            }}
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Status:
          </span>
          <select
            value={acknowledgedFilter}
            onChange={(e) =>
              setAcknowledgedFilter(
                e.target.value as "all" | "acknowledged" | "unacknowledged"
              )
            }
            className="px-3 py-1.5 rounded-lg text-sm border bg-transparent"
            style={{
              borderColor: "var(--base-04)",
              color: "var(--text-primary)",
            }}
          >
            <option value="all">All</option>
            <option value="unacknowledged">Unacknowledged</option>
            <option value="acknowledged">Acknowledged</option>
          </select>
        </div>

        <div className="flex-1" />

        <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          {filteredAlerts.length} alert
          {filteredAlerts.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Alert List */}
      {filteredAlerts.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {filteredAlerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={handleAcknowledge}
              isAcknowledging={acknowledging === alert.id}
            />
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

function AlertCard({
  alert,
  onAcknowledge,
  isAcknowledging,
}: {
  alert: SecurityAlert;
  onAcknowledge: (id: string) => void;
  isAcknowledging: boolean;
}) {
  const severityColor = getSeverityColor(alert.severity);

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: alert.acknowledged
          ? "var(--base-01)"
          : "var(--base-02)",
        borderColor: alert.acknowledged
          ? "var(--base-04)"
          : `${severityColor}40`,
        opacity: alert.acknowledged ? 0.7 : 1,
      }}
    >
      <div className="flex items-start gap-4">
        {/* Severity Indicator */}
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
          style={{
            background: `${severityColor}20`,
          }}
        >
          <AlertSeverityIcon severity={alert.severity} color={severityColor} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h4
                  className="font-medium"
                  style={{ color: "var(--text-primary)" }}
                >
                  {alert.title}
                </h4>
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    background: `${severityColor}20`,
                    color: severityColor,
                  }}
                >
                  {getSeverityLabel(alert.severity)}
                </span>
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    background: "var(--base-03)",
                    color: "var(--text-tertiary)",
                  }}
                >
                  {alert.category}
                </span>
              </div>
              <p
                className="text-sm mb-2"
                style={{ color: "var(--text-secondary)" }}
              >
                {alert.description}
              </p>
              <div
                className="flex items-center gap-4 text-xs"
                style={{ color: "var(--text-tertiary)" }}
              >
                <span>Source: {alert.source}</span>
                <span>{formatTimestamp(alert.timestamp)}</span>
              </div>
            </div>

            {/* Actions */}
            {!alert.acknowledged && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                disabled={isAcknowledging}
                className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 shrink-0"
                style={{
                  background: "var(--base-03)",
                  color: "var(--text-secondary)",
                }}
              >
                {isAcknowledging ? "..." : "Acknowledge"}
              </button>
            )}
            {alert.acknowledged && (
              <span
                className="px-3 py-1.5 rounded-lg text-sm shrink-0"
                style={{
                  background: "var(--base-03)",
                  color: "var(--text-tertiary)",
                }}
              >
                Acknowledged
              </span>
            )}
          </div>

          {/* Related Action */}
          {alert.related_action && (
            <div
              className="mt-3 pt-3 border-t"
              style={{ borderColor: "var(--base-04)" }}
            >
              <a
                href="#"
                className="text-sm hover:underline"
                style={{ color: "var(--accent-primary)" }}
              >
                View related: {alert.related_action}
              </a>
            </div>
          )}
        </div>
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
          stroke="var(--success)"
          strokeWidth="2"
        >
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      </div>
      <h3
        className="text-lg font-medium mb-2"
        style={{ color: "var(--text-primary)" }}
      >
        No Alerts Found
      </h3>
      <p style={{ color: "var(--text-secondary)" }}>
        Security alerts will appear here when threats are detected.
      </p>
    </div>
  );
}

function AlertSeverityIcon({
  severity,
  color,
}: {
  severity: Severity;
  color: string;
}) {
  switch (severity) {
    case "critical":
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      );
    case "high":
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      );
    case "medium":
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      );
    case "low":
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      );
    default:
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      );
  }
}
