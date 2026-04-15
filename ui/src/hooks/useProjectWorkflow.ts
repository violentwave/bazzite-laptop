"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ProjectContext,
  WorkflowRun,
  PhaseTimelineEntry,
  ArtifactInfo,
  NotionSyncStatus,
} from "@/types/project-workflow";
import { callMCPTool } from "@/lib/mcp-client";

interface UseProjectWorkflowReturn {
  context: ProjectContext | null;
  workflows: WorkflowRun[];
  timeline: PhaseTimelineEntry[];
  artifacts: ArtifactInfo[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useProjectWorkflow(): UseProjectWorkflowReturn {
  const [context, setContext] = useState<ProjectContext | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([]);
  const [timeline, setTimeline] = useState<PhaseTimelineEntry[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      let hasError = false;
      const [contextData, workflowsData, timelineData, artifactsData] = await Promise.all([
        callMCPTool("project.context"),
        callMCPTool("project.workflow_history", { limit: 10 }),
        callMCPTool("project.phase_timeline"),
        callMCPTool("project.artifacts", { limit: 10 }),
      ]);

      if (contextData && typeof contextData === "object") {
        if ("error" in contextData) {
          setError(String((contextData as Record<string, unknown>).error || "Context load failed"));
          hasError = true;
        } else if ("success" in contextData && (contextData as Record<string, unknown>).success === false) {
          setError(String((contextData as Record<string, unknown>).error || "Context load failed"));
          hasError = true;
        } else {
          setContext(contextData as ProjectContext);
        }
      }

      if (Array.isArray(workflowsData)) {
        setWorkflows(workflowsData as WorkflowRun[]);
      } else if (workflowsData && typeof workflowsData === "object" && "error" in (workflowsData as Record<string, unknown>)) {
        if (!hasError) {
          setError(
            String((workflowsData as Record<string, unknown>).error || "Workflow history unavailable")
          );
          hasError = true;
        }
      }

      if (Array.isArray(timelineData)) {
        setTimeline(timelineData as PhaseTimelineEntry[]);
      } else if (timelineData && typeof timelineData === "object" && "error" in (timelineData as Record<string, unknown>)) {
        if (!hasError) {
          setError(String((timelineData as Record<string, unknown>).error || "Timeline unavailable"));
          hasError = true;
        }
      }

      if (Array.isArray(artifactsData)) {
        setArtifacts(artifactsData as ArtifactInfo[]);
      } else if (artifactsData && typeof artifactsData === "object" && "error" in (artifactsData as Record<string, unknown>)) {
        // Artifacts failure is non-critical, just log
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? `Project data load failed: ${err.message}`
          : "Project data load failed"
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  return {
    context,
    workflows,
    timeline,
    artifacts,
    isLoading,
    error,
    refresh,
  };
}

/** Get status color for UI */
export function getPhaseStatusColor(status: string | null): string {
  const normalized = status?.toLowerCase().replace(/\s+/g, "_");
  switch (normalized) {
    case "completed":
    case "complete":
    case "done":
      return "var(--success)";
    case "in_progress":
    case "active":
      return "var(--live-cyan)";
    case "ready":
    case "gated":
      return "var(--accent-primary)";
    case "blocked":
      return "var(--danger)";
    case "deferred":
      return "var(--warning)";
    case "cancelled":
      return "var(--text-tertiary)";
    case "planned":
    default:
      return "var(--text-tertiary)";
  }
}

/** Get readiness status color */
export function getReadinessColor(status: string): string {
  switch (status) {
    case "ready":
      return "var(--success)";
    case "blocked":
      return "var(--danger)";
    case "degraded":
      return "var(--warning)";
    case "deferred":
      return "var(--warning)";
    case "in_progress":
      return "var(--live-cyan)";
    default:
      return "var(--text-tertiary)";
  }
}

/** Get Notion sync status color */
export function getNotionSyncColor(status: NotionSyncStatus): string {
  switch (status) {
    case "synced":
      return "var(--success)";
    case "stale":
    case "degraded":
      return "var(--warning)";
    case "unavailable":
    default:
      return "var(--text-tertiary)";
  }
}

/** Get workflow status color */
export function getWorkflowStatusColor(status: string): string {
  switch (status) {
    case "completed":
      return "var(--success)";
    case "running":
      return "var(--live-cyan)";
    case "failed":
      return "var(--danger)";
    case "cancelled":
      return "var(--warning)";
    case "pending":
    default:
      return "var(--text-tertiary)";
  }
}

/** Format bytes to human readable */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/** Format timestamp for display */
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
