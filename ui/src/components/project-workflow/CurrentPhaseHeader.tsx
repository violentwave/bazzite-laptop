"use client";

import { PhaseInfo, LatestCompletedPhase } from "@/types/project-workflow";
import {
  getPhaseStatusColor,
  getReadinessColor,
} from "@/hooks/useProjectWorkflow";

interface CurrentPhaseHeaderProps {
  phase: PhaseInfo | null;
  latestCompleted: LatestCompletedPhase | null;
  isLoading: boolean;
}

export function CurrentPhaseHeader({
  phase,
  latestCompleted,
  isLoading,
}: CurrentPhaseHeaderProps) {
  if (isLoading) {
    return (
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <div className="animate-pulse space-y-3">
          <div
            className="h-4 rounded w-1/3"
            style={{ background: "var(--base-03)" }}
          />
          <div
            className="h-6 rounded w-2/3"
            style={{ background: "var(--base-03)" }}
          />
        </div>
      </div>
    );
  }

  if (!phase || !phase.phase_number) {
    return (
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="text-xs font-medium uppercase tracking-wide mb-2"
          style={{ color: "var(--text-tertiary)" }}
        >
          Current Phase
        </h3>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          No active phase detected. Check HANDOFF.md for phase status.
        </p>
      </div>
    );
  }

  const statusColor = getPhaseStatusColor(phase.status);
  const readinessColor = getReadinessColor(phase.readiness);

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <h3
        className="text-xs font-medium uppercase tracking-wide mb-3"
        style={{ color: "var(--text-tertiary)" }}
      >
        Current Phase
      </h3>

      {/* Phase Number & Name */}
      <div className="mb-4">
        <div className="flex items-center gap-3 mb-1">
          <span
            className="text-2xl font-bold font-mono"
            style={{ color: "var(--accent-primary)" }}
          >
            P{phase.phase_number}
          </span>
          <div
            className="flex items-center gap-1.5 px-2 py-0.5 rounded text-xs"
            style={{
              background: "var(--base-03)",
              color: statusColor,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: statusColor }}
            />
            {phase.readiness === "deferred" ? "Deferred" : (phase.status ?? "Unknown")}
          </div>
          {/* Notion status override badge */}
          {phase.notion_status && phase.notion_status !== phase.status && (
            <div
              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px]"
              style={{
                background: "var(--base-03)",
                color: "var(--accent-primary)",
                border: "1px solid var(--base-04)",
              }}
              title={`Notion status: ${phase.notion_status}`}
            >
              Notion: {phase.notion_status}
            </div>
          )}
        </div>
        <h4
          className="text-base font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          {phase.phase_name}
        </h4>
      </div>

      {/* Readiness */}
      <div
        className="flex items-center gap-2 mb-3 p-2 rounded"
        style={{
          background:
            phase.readiness === "ready"
              ? "rgba(34, 197, 94, 0.1)"
              : phase.readiness === "blocked"
              ? "rgba(239, 68, 68, 0.1)"
              : phase.readiness === "deferred"
              ? "rgba(234, 179, 8, 0.1)"
              : phase.readiness === "in_progress"
              ? "rgba(6, 182, 212, 0.1)"
              : "var(--base-03)",
        }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: readinessColor }}
        />
        <span className="text-sm font-medium" style={{ color: readinessColor }}>
          {phase.readiness === "ready"
            ? "Ready to Execute"
            : phase.readiness === "blocked"
            ? "Blocked"
            : phase.readiness === "deferred"
            ? "Deferred"
            : phase.readiness === "in_progress"
            ? "In Progress"
            : "Not Ready"}
        </span>
      </div>

      {/* Blockers */}
      {phase.blockers.length > 0 && (
        <div className="mb-3">
          <h5
            className="text-xs font-medium mb-2"
            style={{ color: "var(--text-tertiary)" }}
          >
            Blockers
          </h5>
          <ul className="space-y-1">
            {phase.blockers.map((blocker, index) => (
              <li
                key={index}
                className="text-xs flex items-start gap-1.5"
                style={{ color: "var(--danger)" }}
              >
                <span>•</span>
                <span>{blocker}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next Action */}
      {phase.next_action && (
        <div
          className="p-2 rounded border-l-2"
          style={{
            background: "var(--base-03)",
            borderColor: "var(--accent-primary)",
          }}
        >
          <h5
            className="text-xs font-medium mb-1"
            style={{ color: "var(--text-tertiary)" }}
          >
            Next Action
          </h5>
          <p className="text-sm" style={{ color: "var(--text-primary)" }}>
            {phase.next_action}
          </p>
        </div>
      )}

      {/* Latest Completed Phase */}
      {latestCompleted && (
        <div
          className="mt-3 pt-3 border-t flex items-center gap-2 text-xs"
          style={{ borderColor: "var(--base-04)" }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: "var(--success)" }}
          />
          <span style={{ color: "var(--text-tertiary)" }}>
            Latest completed:
          </span>
          <span
            className="font-mono"
            style={{ color: "var(--text-secondary)" }}
          >
            P{latestCompleted.phase_number}
          </span>
          <span style={{ color: "var(--text-tertiary)" }}>—</span>
          <span
            className="truncate"
            style={{ color: "var(--text-secondary)" }}
          >
            {latestCompleted.phase_name}
          </span>
        </div>
      )}

      {/* Meta */}
      <div className="mt-3 pt-3 border-t flex items-center gap-4 text-xs" style={{ borderColor: "var(--base-04)" }}>
        <div style={{ color: "var(--text-tertiary)" }}>
          Backend: <span style={{ color: "var(--text-secondary)" }}>{phase.backend}</span>
        </div>
        <div style={{ color: "var(--text-tertiary)" }}>
          Risk: <span style={{ color: "var(--text-secondary)" }}>{phase.risk_tier}</span>
        </div>
      </div>
    </div>
  );
}