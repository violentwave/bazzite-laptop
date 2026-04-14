"use client";

import { ShellSession, SessionContext } from "@/types/shell";
import { formatSessionTime, formatIdleTime } from "@/hooks/useShellSessions";

interface ShellAuditStripProps {
  session: ShellSession | null;
  context: SessionContext | null;
}

export function ShellAuditStrip({ session, context }: ShellAuditStripProps) {
  if (!session) {
    return (
      <div
        className="flex items-center justify-between px-4 py-2 text-xs border-t"
        style={{
          background: "var(--base-01)",
          borderColor: "var(--base-04)",
          color: "var(--text-tertiary)",
        }}
      >
        <span>No active session</span>
        <span>--:--</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-between px-4 py-2 text-xs border-t"
      style={{
        background: "var(--base-01)",
        borderColor: "var(--base-04)",
        color: "var(--text-secondary)",
      }}
    >
      <div className="flex items-center gap-4">
        {/* Session ID */}
        <div className="flex items-center gap-1.5">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{ color: "var(--text-tertiary)" }}
          >
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          <span style={{ color: "var(--text-tertiary)" }}>ID:</span>
          <span className="font-mono">{session.id}</span>
        </div>

        {/* User/Host */}
        {context && (
          <div className="flex items-center gap-1.5">
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ color: "var(--text-tertiary)" }}
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span style={{ color: "var(--text-tertiary)" }}>User:</span>
            <span>{context.user}@{context.hostname}</span>
          </div>
        )}

        {/* Shell Type */}
        <div className="flex items-center gap-1.5">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{ color: "var(--text-tertiary)" }}
          >
            <polyline points="4 17 10 11 4 5" />
            <line x1="12" y1="19" x2="20" y2="19" />
          </svg>
          <span style={{ color: "var(--text-tertiary)" }}>Shell:</span>
          <span className="font-mono">{context?.shell || "bash"}</span>
        </div>

        {/* Idle Time */}
        {context && context.idle_time > 0 && (
          <div className="flex items-center gap-1.5">
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ color: "var(--text-tertiary)" }}
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span style={{ color: "var(--text-tertiary)" }}>Idle:</span>
            <span>{formatIdleTime(context.idle_time)}</span>
          </div>
        )}

        {/* Command Count */}
        {session.command_history.length > 0 && (
          <div className="flex items-center gap-1.5">
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ color: "var(--text-tertiary)" }}
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span style={{ color: "var(--text-tertiary)" }}>Commands:</span>
            <span>{session.command_history.length}</span>
          </div>
        )}
      </div>

      {/* Timestamp */}
      <div className="flex items-center gap-1.5">
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{ color: "var(--text-tertiary)" }}
        >
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        <span style={{ color: "var(--text-tertiary)" }}>Started:</span>
        <span>{formatSessionTime(session.created_at)}</span>
      </div>
    </div>
  );
}
