"use client";

import { ShellSession } from "@/types/shell";
import { getSessionStatusColor } from "@/hooks/useShellSessions";

interface SessionTabsProps {
  sessions: ShellSession[];
  activeSession: ShellSession | null;
  onSelectSession: (session: ShellSession) => void;
  onCreateSession: () => void;
  onTerminateSession: (sessionId: string) => void;
}

export function SessionTabs({
  sessions,
  activeSession,
  onSelectSession,
  onCreateSession,
  onTerminateSession,
}: SessionTabsProps) {
  if (sessions.length === 0) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-1 px-2 py-2 border-b overflow-x-auto"
      style={{
        background: "var(--base-01)",
        borderColor: "var(--base-04)",
      }}
    >
      {sessions.map((session) => {
        const isActive = activeSession?.id === session.id;
        const statusColor = getSessionStatusColor(session.status);

        return (
          <div
            key={session.id}
            onClick={() => onSelectSession(session)}
            className="group flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer transition-colors min-w-fit"
            style={{
              background: isActive ? "var(--base-03)" : "transparent",
              border: isActive ? "1px solid var(--base-04)" : "1px solid transparent",
            }}
          >
            {/* Status Dot */}
            <span
              className={`w-2 h-2 rounded-full ${session.status === "active" ? "animate-pulse" : ""}`}
              style={{ background: statusColor }}
            />

            {/* Session Name */}
            <span
              className="text-xs font-medium truncate max-w-[120px]"
              style={{
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
              }}
            >
              {session.name}
            </span>

            {/* Close Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onTerminateSession(session.id);
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded"
              style={{
                color: "var(--text-tertiary)",
              }}
              title="Terminate session"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        );
      })}

      {/* New Session Button */}
      <button
        onClick={onCreateSession}
        className="flex items-center justify-center w-8 h-8 rounded-md transition-colors ml-1"
        style={{
          background: "transparent",
          color: "var(--text-tertiary)",
        }}
        title="Create new session"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </div>
  );
}
