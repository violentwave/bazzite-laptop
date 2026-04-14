"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ProjectContext,
  WorkflowRun,
  PhaseTimelineEntry,
  ArtifactInfo,
} from "@/types/project-workflow";

interface UseProjectWorkflowReturn {
  context: ProjectContext | null;
  workflows: WorkflowRun[];
  timeline: PhaseTimelineEntry[];
  artifacts: ArtifactInfo[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const MCP_BRIDGE_URL = "http://127.0.0.1:8766/tools/call";

async function callMCPTool(name: string, args?: Record<string, unknown>) {
  const response = await fetch(MCP_BRIDGE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, args }),
  });

  if (!response.ok) {
    throw new Error(`MCP tool ${name} failed: ${response.statusText}`);
  }

  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
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
      // Fetch all data in parallel
      const [contextData, workflowsData, timelineData, artifactsData] = await Promise.all([
        callMCPTool("project.context"),
        callMCPTool("project.workflow_history", { limit: 10 }),
        callMCPTool("project.phase_timeline"),
        callMCPTool("project.artifacts", { limit: 10 }),
      ]);

      if (contextData && !contextData.error) {
        setContext(contextData as ProjectContext);
      }

      if (Array.isArray(workflowsData)) {
        setWorkflows(workflowsData as WorkflowRun[]);
      }

      if (Array.isArray(timelineData)) {
        setTimeline(timelineData as PhaseTimelineEntry[]);
      }

      if (Array.isArray(artifactsData)) {
        setArtifacts(artifactsData as ArtifactInfo[]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch project data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load data on mount and refresh periodically
  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000); // Refresh every 30 seconds
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
  switch (status?.toLowerCase()) {
    case "completed":
      return "var(--success)";
    case "in_progress":
      return "var(--live-cyan)";
    case "ready":
      return "var(--accent-primary)";
    case "blocked":
      return "var(--danger)";
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
