"use client";

import { WorkbenchTestCommand, WorkbenchTestExecution } from "@/types/agent-workbench";

interface TestResultsPanelProps {
  selectedProjectId: string | null;
  commands: WorkbenchTestCommand[];
  execution: WorkbenchTestExecution | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => Promise<void>;
  onRun: (commandName: string) => Promise<void>;
}

export function TestResultsPanel({
  selectedProjectId,
  commands,
  execution,
  isLoading,
  error,
  onRefresh,
  onRun,
}: TestResultsPanelProps) {
  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            Test Results
          </h3>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Runs only registered safe commands from `workbench.test_commands`.
          </p>
        </div>
        <button
          onClick={() => void onRefresh()}
          className="px-2.5 py-1.5 rounded-md text-xs"
          style={{ background: "var(--base-03)", color: "var(--text-secondary)" }}
          disabled={isLoading || !selectedProjectId}
        >
          {isLoading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          className="rounded-lg border-l-2 p-3 text-xs"
          style={{ borderColor: "var(--warning)", background: "rgba(245, 158, 11, 0.08)", color: "var(--text-secondary)" }}
        >
          {error}
        </div>
      )}

      {!selectedProjectId ? (
        <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Select a project to view available test commands.
        </p>
      ) : commands.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          No registered test commands found for this project.
        </p>
      ) : (
        <div className="space-y-2">
          {commands.map((command) => (
            <div
              key={command.name}
              className="rounded-lg border p-3"
              style={{ borderColor: "var(--base-04)", background: "var(--base-01)" }}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm" style={{ color: "var(--text-primary)" }}>
                    {command.name}
                  </div>
                  <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    {command.description}
                  </div>
                </div>
                <button
                  onClick={() => void onRun(command.name)}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: command.enabled ? "var(--accent-primary)" : "var(--base-03)",
                    color: "white",
                  }}
                  disabled={!command.enabled || isLoading}
                >
                  Run
                </button>
              </div>
              <div className="mt-2 text-xs" style={{ color: "var(--text-tertiary)" }}>
                timeout={command.timeout_seconds}s · cmd={command.command.join(" ")}
              </div>
            </div>
          ))}
        </div>
      )}

      {execution && (
        <div
          className="rounded-lg border p-3"
          style={{
            borderColor: execution.success ? "var(--success)" : "var(--danger)",
            background: "var(--base-01)",
          }}
        >
          <div className="flex items-center justify-between text-xs mb-2">
            <span style={{ color: "var(--text-secondary)" }}>
              last run: {execution.command.name}
            </span>
            <span style={{ color: execution.success ? "var(--success)" : "var(--danger)" }}>
              exit={execution.exit_code}
            </span>
          </div>
          <pre
            className="text-xs overflow-auto max-h-48 rounded p-2"
            style={{
              background: "var(--base-00)",
              color: "var(--text-secondary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {execution.output || "(no output)"}
          </pre>
        </div>
      )}
    </div>
  );
}
