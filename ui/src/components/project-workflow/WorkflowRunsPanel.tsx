"use client";

import { WorkflowRun } from "@/types/project-workflow";
import {
  getWorkflowStatusColor,
  formatTimestamp,
} from "@/hooks/useProjectWorkflow";

interface WorkflowRunsPanelProps {
  workflows: WorkflowRun[];
  isLoading: boolean;
}

export function WorkflowRunsPanel({ workflows, isLoading }: WorkflowRunsPanelProps) {
  if (isLoading) {
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
          Recent Workflow Runs
        </h3>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-12 rounded"
              style={{ background: "var(--base-03)" }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3
          className="text-xs font-medium uppercase tracking-wide"
          style={{ color: "var(--text-tertiary)" }}
        >
          Recent Workflow Runs
        </h3>
        <span
          className="text-xs px-2 py-0.5 rounded-full"
          style={{
            background: "var(--base-03)",
            color: "var(--text-secondary)",
          }}
        >
          {workflows.length}
        </span>
      </div>

      {workflows.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          No recent workflow runs
        </p>
      ) : (
        <div className="space-y-2">
          {workflows.slice(0, 5).map((workflow) => {
            const statusColor = getWorkflowStatusColor(workflow.status);
            return (
              <div
                key={workflow.run_id}
                className="p-3 rounded border transition-colors hover:border-opacity-50"
                style={{
                  background: "var(--base-01)",
                  borderColor: "var(--base-04)",
                }}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        workflow.status === "running" ? "animate-pulse" : ""
                      }`}
                      style={{ background: statusColor }}
                    />
                    <span
                      className="text-sm font-medium"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {workflow.workflow_name}
                    </span>
                  </div>
                  <span
                    className="text-xs"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    {formatTimestamp(workflow.started_at)}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-xs">
                  <span style={{ color: "var(--text-secondary)" }}>
                    Status: <span style={{ color: statusColor }}>{workflow.status}</span>
                  </span>
                  {workflow.step_count > 0 && (
                    <span style={{ color: "var(--text-secondary)" }}>
                      Steps: {workflow.step_count}
                    </span>
                  )}
                </div>

                {workflow.error_message && (
                  <p
                    className="mt-2 text-xs truncate"
                    style={{ color: "var(--danger)" }}
                  >
                    {workflow.error_message}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
