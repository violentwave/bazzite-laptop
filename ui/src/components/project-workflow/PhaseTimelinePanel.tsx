"use client";

import { PhaseTimelineEntry } from "@/types/project-workflow";
import { getPhaseStatusColor } from "@/hooks/useProjectWorkflow";

interface PhaseTimelinePanelProps {
  timeline: PhaseTimelineEntry[];
  isLoading: boolean;
}

export function PhaseTimelinePanel({ timeline, isLoading }: PhaseTimelinePanelProps) {
  if (isLoading) {
    return (
      <div
        className="p-4 rounded-lg border h-full"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="text-xs font-medium uppercase tracking-wide mb-3"
          style={{ color: "var(--text-tertiary)" }}
        >
          Phase Timeline
        </h3>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-8 rounded"
              style={{ background: "var(--base-03)" }}
            />
          ))}
        </div>
      </div>
    );
  }

  // Sort by phase number
  const sortedTimeline = [...timeline].sort((a, b) => a.number - b.number);

  return (
    <div
      className="p-4 rounded-lg border h-full"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <h3
        className="text-xs font-medium uppercase tracking-wide mb-3"
        style={{ color: "var(--text-tertiary)" }}
      >
        Phase Timeline
      </h3>

      {sortedTimeline.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          No phase documentation found
        </p>
      ) : (
        <div className="space-y-1 max-h-96 overflow-auto">
          {sortedTimeline.map((phase, index) => {
            const statusColor = getPhaseStatusColor(phase.status);
            const isLast = index === sortedTimeline.length - 1;

            return (
              <div key={phase.number} className="flex items-start gap-3">
                {/* Timeline Line */}
                <div className="flex flex-col items-center flex-shrink-0">
                  <div
                    className="w-3 h-3 rounded-full border-2"
                    style={{
                      background:
                        phase.status === "in_progress"
                          ? statusColor
                          : "var(--base-02)",
                      borderColor: statusColor,
                    }}
                  />
                  {!isLast && (
                    <div
                      className="w-0.5 flex-1 min-h-[20px]"
                      style={{ background: "var(--base-04)" }}
                    />
                  )}
                </div>

                {/* Phase Info */}
                <div
                  className="flex-1 pb-3"
                  style={{
                    opacity: phase.status === "planned" ? 0.6 : 1,
                  }}
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className="text-sm font-mono font-medium"
                      style={{ color: statusColor }}
                    >
                      P{phase.number}
                    </span>
                    {phase.status === "in_progress" && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{
                          background: "var(--base-03)",
                          color: "var(--live-cyan)",
                        }}
                      >
                        Active
                      </span>
                    )}
                  </div>
                  <p
                    className="text-xs truncate"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {phase.name.replace(`P${phase.number}`, "").trim()}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
