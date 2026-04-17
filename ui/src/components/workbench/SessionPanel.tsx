"use client";

import { WorkbenchSession } from "@/types/agent-workbench";

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function sessionColor(status: string): string {
  if (status === "active") return "var(--success)";
  if (status === "stopped") return "var(--warning)";
  return "var(--text-tertiary)";
}

interface SessionPanelProps {
  sessions: WorkbenchSession[];
  selectedSessionId: string | null;
  selectedProjectId: string | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => Promise<void>;
  onCreate: () => Promise<void>;
  onAttach: (sessionId: string) => Promise<void>;
  onStop: (sessionId: string) => Promise<void>;
}

export function SessionPanel({
  sessions,
  selectedSessionId,
  selectedProjectId,
  isLoading,
  error,
  onRefresh,
  onCreate,
  onAttach,
  onStop,
}: SessionPanelProps) {
  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            Session Terminal
          </h3>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Create, attach, and stop bounded workbench sessions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void onRefresh()}
            className="px-2.5 py-1.5 rounded-md text-xs"
            style={{ background: "var(--base-03)", color: "var(--text-secondary)" }}
            disabled={isLoading || !selectedProjectId}
          >
            Refresh
          </button>
          <button
            onClick={() => void onCreate()}
            className="px-2.5 py-1.5 rounded-md text-xs"
            style={{ background: "var(--accent-primary)", color: "white" }}
            disabled={isLoading || !selectedProjectId}
          >
            + Session
          </button>
        </div>
      </div>

      {error && (
        <div
          className="rounded-lg border-l-2 p-3 text-xs"
          style={{ borderColor: "var(--danger)", background: "rgba(239, 68, 68, 0.08)", color: "var(--text-secondary)" }}
        >
          {error}
        </div>
      )}

      {!selectedProjectId ? (
        <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Select a project to manage workbench sessions.
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          No sessions yet for this project.
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => {
            const isActiveSelection = session.session_id === selectedSessionId;
            return (
              <div
                key={session.session_id}
                className="rounded-lg border p-3"
                style={{
                  borderColor: isActiveSelection ? "var(--accent-primary)" : "var(--base-04)",
                  background: "var(--base-01)",
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm" style={{ color: "var(--text-primary)" }}>
                      {session.session_id}
                    </div>
                    <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                      backend={session.backend} · profile={session.sandbox_profile}
                    </div>
                  </div>
                  <span
                    className="text-xs px-2 py-1 rounded-full"
                    style={{ background: "var(--base-03)", color: sessionColor(session.status) }}
                  >
                    {session.status}
                  </span>
                </div>
                <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
                  cwd={session.cwd}
                </div>
                <div className="mt-1 text-xs" style={{ color: "var(--text-tertiary)" }}>
                  created={formatTime(session.created_at)} · updated={formatTime(session.updated_at)}
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={() => void onAttach(session.session_id)}
                    className="px-2 py-1 rounded text-xs"
                    style={{ background: "var(--base-03)", color: "var(--text-secondary)" }}
                  >
                    Attach
                  </button>
                  <button
                    onClick={() => void onStop(session.session_id)}
                    disabled={session.status !== "active"}
                    className="px-2 py-1 rounded text-xs disabled:opacity-60"
                    style={{ background: "rgba(239, 68, 68, 0.2)", color: "var(--danger)" }}
                  >
                    Stop
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
