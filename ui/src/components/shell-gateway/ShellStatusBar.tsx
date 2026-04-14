"use client";

import { ShellSession, SessionContext } from "@/types/shell";
import { getSessionStatusColor, formatIdleTime } from "@/hooks/useShellSessions";

interface ShellStatusBarProps {
  session: ShellSession | null;
  context: SessionContext | null;
  isLoading: boolean;
  error: string | null;
}

export function ShellStatusBar({
  session,
  context,
  isLoading,
  error,
}: ShellStatusBarProps) {
  // Error state takes precedence
  if (error) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
        style={{
          background: "rgba(239, 68, 68, 0.1)",
          color: "var(--danger)",
          border: "1px solid var(--base-04)",
        }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: "var(--danger)" }}
        />
        Error
      </div>
    );
  }

  // No session
  if (!session) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
        style={{
          background: "var(--base-02)",
          color: "var(--text-tertiary)",
          border: "1px solid var(--base-04)",
        }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: "var(--text-tertiary)" }}
        />
        No Session
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
        style={{
          background: "var(--base-02)",
          color: "var(--warning)",
          border: "1px solid var(--base-04)",
        }}
      >
        <span
          className="w-2 h-2 rounded-full animate-pulse"
          style={{ background: "var(--warning)" }}
        />
        Processing
      </div>
    );
  }

  // Session status
  const statusColor = getSessionStatusColor(session.status);
  const isIdle = context && context.idle_time > 60;

  // Determine display status
  let displayStatus = session.status;
  let displayColor = statusColor;

  if (session.status === "active" && isIdle) {
    displayStatus = "idle";
    displayColor = "var(--warning)";
  }

  const statusLabels: Record<string, string> = {
    active: "Live",
    idle: "Idle",
    disconnected: "Disconnected",
    error: "Error",
  };

  return (
    <div className="flex items-center gap-2">
      {/* Main Status Chip */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
        style={{
          background: "var(--base-02)",
          color: displayColor,
          border: "1px solid var(--base-04)",
        }}
      >
        <span
          className={`w-2 h-2 rounded-full ${displayStatus === "active" ? "animate-pulse" : ""}`}
          style={{ background: displayColor }}
        />
        {statusLabels[displayStatus] || displayStatus}
      </div>

      {/* Idle Time Badge */}
      {isIdle && context && (
        <div
          className="flex items-center gap-1.5 px-2 py-1 rounded text-xs"
          style={{
            background: "rgba(245, 158, 11, 0.1)",
            color: "var(--warning)",
          }}
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          {formatIdleTime(context.idle_time)}
        </div>
      )}

      {/* PID Badge */}
      {session.pid && (
        <div
          className="flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono"
          style={{
            background: "var(--base-02)",
            color: "var(--text-tertiary)",
          }}
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="2" y="3" width="20" height="14" rx="2" />
            <line x1="8" y1="21" x2="16" y2="21" />
            <line x1="12" y1="17" x2="12" y2="21" />
          </svg>
          PID:{session.pid}
        </div>
      )}
    </div>
  );
}
