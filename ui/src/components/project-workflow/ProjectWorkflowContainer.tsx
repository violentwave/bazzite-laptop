"use client";

import { useProjectWorkflow } from "@/hooks/useProjectWorkflow";
import { getNotionSyncColor } from "@/hooks/useProjectWorkflow";
import { CurrentPhaseHeader } from "./CurrentPhaseHeader";
import { WorkflowRunsPanel } from "./WorkflowRunsPanel";
import { ArtifactHistoryPanel } from "./ArtifactHistoryPanel";
import { PhaseTimelinePanel } from "./PhaseTimelinePanel";
import { NextActionsPanel } from "./NextActionsPanel";
import type { NotionSyncStatus } from "@/types/project-workflow";

export function ProjectWorkflowContainer() {
  const { context, workflows, timeline, artifacts, isLoading, error, refresh } =
    useProjectWorkflow();

  const notionSync = context?.notion_sync_status ?? "unavailable";
  const notionMessage = context?.notion_sync_message ?? "";

  return (
    <div
      className="h-full flex flex-col overflow-hidden"
      style={{ background: "var(--base-00)" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{
          background: "var(--base-01)",
          borderColor: "var(--base-04)",
        }}
      >
        <div className="flex items-center gap-4">
          <h2
            className="text-sm font-medium"
            style={{ color: "var(--text-primary)" }}
          >
            Projects & Workflow
          </h2>
          {context && (
            <div
              className="flex items-center gap-2 px-3 py-1 rounded-full text-xs"
              style={{
                background: "var(--base-02)",
                border: "1px solid var(--base-04)",
              }}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{
                  background:
                    context.preflight_status === "pass"
                      ? "var(--success)"
                      : context.preflight_status === "fail"
                      ? "var(--danger)"
                      : "var(--warning)",
                }}
              />
              <span style={{ color: "var(--text-secondary)" }}>
                {context.preflight_status === "pass"
                  ? "Ready"
                  : context.preflight_status === "fail"
                  ? "Blocked"
                  : "Warning"}
              </span>
            </div>
          )}
          {/* Notion sync status badge */}
          <div
            className="flex items-center gap-1.5 px-2 py-1 rounded text-xs"
            style={{
              background: "var(--base-02)",
              color: getNotionSyncColor(notionSync as NotionSyncStatus),
              border: "1px solid var(--base-04)",
            }}
            title={notionMessage}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: getNotionSyncColor(notionSync as NotionSyncStatus) }}
            />
            {notionSync === "synced" && "Notion synced"}
            {notionSync === "unavailable" && "Local only"}
            {notionSync === "degraded" && "Sync degraded"}
            {notionSync === "stale" && "Sync stale"}
          </div>
        </div>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="px-3 py-1.5 text-xs rounded transition-colors disabled:opacity-50"
          style={{
            background: "var(--base-02)",
            color: "var(--text-secondary)",
            border: "1px solid var(--base-04)",
          }}
        >
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Notion status message (when degraded/unavailable) */}
      {context && notionSync !== "synced" && notionMessage && (
        <div
          className="mx-4 mt-3 p-2 rounded border-l-2 text-xs"
          style={{
            background: notionSync === "unavailable"
              ? "rgba(156, 163, 175, 0.08)"
              : "rgba(234, 179, 8, 0.08)",
            borderColor: notionSync === "unavailable"
              ? "var(--text-tertiary)"
              : "var(--warning)",
            color: "var(--text-secondary)",
          }}
        >
          {notionMessage}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div
          className="mx-4 mt-4 p-3 rounded-lg border-l-2"
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            borderColor: "var(--danger)",
          }}
        >
          <p className="text-sm" style={{ color: "var(--danger)" }}>
            {error}
          </p>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-12 gap-4">
          {/* Left Column - Current Phase & Actions */}
          <div className="col-span-12 lg:col-span-4 space-y-4">
            <CurrentPhaseHeader
              phase={context?.current_phase || null}
              latestCompleted={context?.latest_completed_phase || null}
              isLoading={isLoading}
            />
            <NextActionsPanel
              recommendations={context?.recommendations || []}
              isLoading={isLoading}
            />
          </div>

          {/* Middle Column - Timeline */}
          <div className="col-span-12 lg:col-span-4">
            <PhaseTimelinePanel timeline={timeline} isLoading={isLoading} />
          </div>

          {/* Right Column - Workflows & Artifacts */}
          <div className="col-span-12 lg:col-span-4 space-y-4">
            <WorkflowRunsPanel workflows={workflows} isLoading={isLoading} />
            <ArtifactHistoryPanel artifacts={artifacts} isLoading={isLoading} />
          </div>
        </div>
      </div>
    </div>
  );
}