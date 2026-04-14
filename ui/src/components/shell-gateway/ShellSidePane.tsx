"use client";

import { useState, useEffect } from "react";
import { ShellSession } from "@/types/shell";
import { useShellSessions } from "@/hooks/useShellSessions";

interface ShellSidePaneProps {
  activeTab: "logs" | "artifacts";
  onTabChange: (tab: "logs" | "artifacts") => void;
  session: ShellSession | null;
}

export function ShellSidePane({
  activeTab,
  onTabChange,
  session,
}: ShellSidePaneProps) {
  const { getAuditLog } = useShellSessions();
  const [auditEntries, setAuditEntries] = useState<Array<{
    timestamp: string;
    action: string;
    session_id: string;
    details: Record<string, unknown>;
  }>>([]);

  useEffect(() => {
    if (activeTab === "logs" && session) {
      getAuditLog(session.id, 20).then(setAuditEntries);
    }
  }, [activeTab, session, getAuditLog]);

  return (
    <div
      className="w-80 border-l flex flex-col"
      style={{
        background: "var(--base-01)",
        borderColor: "var(--base-04)",
      }}
    >
      {/* Pane Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--base-04)" }}
      >
        <h3
          className="text-sm font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          {activeTab === "logs" ? "Session Logs" : "Artifacts"}
        </h3>
      </div>

      {/* Tab Navigation */}
      <div
        className="flex items-center gap-1 px-2 py-2 border-b"
        style={{ borderColor: "var(--base-04)" }}
      >
        <button
          onClick={() => onTabChange("logs")}
          className="flex-1 px-3 py-1.5 text-xs rounded transition-colors"
          style={{
            background: activeTab === "logs" ? "var(--base-03)" : "transparent",
            color: activeTab === "logs" ? "var(--text-primary)" : "var(--text-secondary)",
          }}
        >
          Audit Log
        </button>
        <button
          onClick={() => onTabChange("artifacts")}
          className="flex-1 px-3 py-1.5 text-xs rounded transition-colors"
          style={{
            background: activeTab === "artifacts" ? "var(--base-03)" : "transparent",
            color: activeTab === "artifacts" ? "var(--text-primary)" : "var(--text-secondary)",
          }}
        >
          Artifacts
        </button>
      </div>

      {/* Pane Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === "logs" ? (
          <AuditLogView entries={auditEntries} session={session} />
        ) : (
          <ArtifactsView session={session} />
        )}
      </div>
    </div>
  );
}

function AuditLogView({
  entries,
  session,
}: {
  entries: Array<{
    timestamp: string;
    action: string;
    session_id: string;
    details: Record<string, unknown>;
  }>;
  session: ShellSession | null;
}) {
  if (!session) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          Select a session to view audit log
        </p>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          No audit entries for this session
        </p>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1">
      {entries.map((entry, index) => (
        <div
          key={index}
          className="p-2 rounded text-xs"
          style={{ background: "var(--base-02)" }}
        >
          <div className="flex items-center justify-between mb-1">
            <span
              className="font-medium"
              style={{
                color:
                  entry.action === "command_executed"
                    ? "var(--accent-primary)"
                    : entry.action === "session_terminated"
                    ? "var(--danger)"
                    : "var(--text-secondary)",
              }}
            >
              {entry.action.replace(/_/g, " ")}
            </span>
            <span style={{ color: "var(--text-tertiary)" }}>
              {new Date(entry.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
          </div>
          {entry.details && Object.keys(entry.details).length > 0 ? (
            <div className="mt-1 space-y-0.5">
              {entry.details.command ? (
                <div className="font-mono truncate" style={{ color: "var(--text-secondary)" }}>
                  $ {String(entry.details.command)}
                </div>
              ) : null}
              {entry.details.exit_code !== undefined ? (
                <div
                  style={{
                    color:
                      entry.details.exit_code === 0
                        ? "var(--success)"
                        : "var(--danger)",
                  }}
                >
                  Exit code: {String(entry.details.exit_code)}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function ArtifactsView({ session }: { session: ShellSession | null }) {
  if (!session) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          Select a session to view artifacts
        </p>
      </div>
    );
  }

  // Placeholder for artifact files
  const artifacts = session.command_history.length > 0
    ? [
        {
          name: "command-history.txt",
          type: "text",
          size: `${session.command_history.length} commands`,
          time: "Current session",
        },
      ]
    : [];

  if (artifacts.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          No artifacts generated yet
        </p>
        <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
          Artifacts will appear here when available
        </p>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1">
      {artifacts.map((artifact, index) => (
        <div
          key={index}
          className="flex items-center gap-3 p-3 rounded cursor-pointer transition-colors"
          style={{
            background: "var(--base-02)",
          }}
        >
          {/* File Icon */}
          <div
            className="w-8 h-8 rounded flex items-center justify-center"
            style={{ background: "var(--base-03)" }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ color: "var(--text-secondary)" }}
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>

          {/* Artifact Info */}
          <div className="flex-1 min-w-0">
            <div
              className="text-xs font-medium truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {artifact.name}
            </div>
            <div
              className="text-xs"
              style={{ color: "var(--text-tertiary)" }}
            >
              {artifact.size}
            </div>
          </div>

          {/* Time */}
          <div
            className="text-xs"
            style={{ color: "var(--text-tertiary)" }}
          >
            {artifact.time}
          </div>
        </div>
      ))}
    </div>
  );
}
