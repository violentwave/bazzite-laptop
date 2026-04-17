"use client";

import { WorkbenchProject, WorkbenchProjectStatus } from "@/types/agent-workbench";

function formatTime(value?: string | null): string {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function redactPath(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length <= 2) {
    return normalized;
  }
  return `.../${parts.slice(-2).join("/")}`;
}

interface ProjectPickerProps {
  projects: WorkbenchProject[];
  selectedProjectId: string | null;
  projectStatus: WorkbenchProjectStatus | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => Promise<void>;
  onSelectProject: (projectId: string | null) => void;
}

export function ProjectPicker({
  projects,
  selectedProjectId,
  projectStatus,
  isLoading,
  error,
  onRefresh,
  onSelectProject,
}: ProjectPickerProps) {
  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            Project Picker
          </h3>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Registered projects only (no fake entries)
          </p>
        </div>
        <button
          onClick={() => void onRefresh()}
          className="px-3 py-1.5 rounded-md text-xs"
          style={{ background: "var(--base-03)", color: "var(--text-secondary)" }}
          disabled={isLoading}
        >
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          className="rounded-lg border-l-2 p-3 text-xs"
          style={{
            borderColor: "var(--warning)",
            background: "rgba(245, 158, 11, 0.08)",
            color: "var(--text-secondary)",
          }}
        >
          {error}
        </div>
      )}

      <select
        value={selectedProjectId || ""}
        onChange={(event) => onSelectProject(event.target.value || null)}
        className="w-full px-3 py-2 rounded-lg text-sm"
        style={{
          background: "var(--base-01)",
          border: "1px solid var(--base-04)",
          color: "var(--text-primary)",
        }}
      >
        <option value="">Select a registered project</option>
        {projects.map((project) => (
          <option key={project.project_id} value={project.project_id}>
            {project.name} ({project.project_id})
          </option>
        ))}
      </select>

      {projects.length === 0 && !isLoading && (
        <div
          className="rounded-lg p-3 text-xs"
          style={{ background: "var(--base-01)", color: "var(--text-secondary)" }}
        >
          No registered workbench projects were found. Register a project through MCP first.
        </div>
      )}

      {projectStatus && (
        <div className="grid grid-cols-1 gap-2 text-xs">
          <div className="flex items-center justify-between">
            <span style={{ color: "var(--text-tertiary)" }}>Root</span>
            <span style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
              {redactPath(projectStatus.project.root_path)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ color: "var(--text-tertiary)" }}>Filesystem</span>
            <span style={{ color: projectStatus.exists ? "var(--success)" : "var(--danger)" }}>
              {projectStatus.exists && projectStatus.is_dir ? "available" : "missing"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ color: "var(--text-tertiary)" }}>Opened</span>
            <span style={{ color: "var(--text-secondary)" }}>
              {formatTime(projectStatus.project.last_opened_at)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ color: "var(--text-tertiary)" }}>Updated</span>
            <span style={{ color: "var(--text-secondary)" }}>
              {formatTime(projectStatus.project.updated_at)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
