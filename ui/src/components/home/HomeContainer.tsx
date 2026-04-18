"use client";

import { ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { useShell } from "@/components/shell/ShellContext";
import { useAgentWorkbench } from "@/hooks/useAgentWorkbench";
import { useProjectWorkflow } from "@/hooks/useProjectWorkflow";
import { useProviders } from "@/hooks/useProviders";
import { useSecurity } from "@/hooks/useSecurity";
import { callMCPTool } from "@/lib/mcp-client";
import {
  THREADS_STORAGE_KEY,
  buildProjectRegisterArgs,
  extractRecentThreads,
  markThreadActive,
  summarizeRuntimeOverview,
  summarizeSecurityWidget,
  type HomeThreadSummary,
} from "@/lib/home-dashboard";
import { buildHomeSystemStatus } from "@/lib/console-simplify";
import { WorkbenchProject } from "@/types/agent-workbench";

type ProjectRegisterResponse = {
  success?: boolean;
  project?: WorkbenchProject;
  error?: string;
};

function formatRelativeTime(timestamp: string): string {
  const value = new Date(timestamp).getTime();
  if (!Number.isFinite(value)) {
    return "unknown";
  }

  const deltaMs = Date.now() - value;
  const minutes = Math.floor(deltaMs / 60000);
  const hours = Math.floor(deltaMs / 3600000);
  const days = Math.floor(deltaMs / 86400000);

  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;

  return new Date(timestamp).toLocaleDateString();
}

export function HomeContainer() {
  const { setActivePanel } = useShell();

  const {
    projects,
    selectedProjectId,
    selectedProject,
    setSelectedProjectId,
    openProject,
    refreshProjects,
    isLoadingProjects,
    error: workbenchError,
  } = useAgentWorkbench();
  const { context, refresh: refreshProjectContext } = useProjectWorkflow();
  const {
    providers,
    models,
    counts,
    isLoading: providersLoading,
    error: providersError,
    refresh: refreshProviders,
    lastRefresh: providersLastRefresh,
  } = useProviders();
  const {
    overview,
    alerts,
    findings,
    systemHealth,
    isLoading: securityLoading,
    error: securityError,
    refresh: refreshSecurity,
    partialData,
    missingSources,
  } = useSecurity();

  const [recentThreads, setRecentThreads] = useState<HomeThreadSummary[]>([]);
  const [showCreateProjectModal, setShowCreateProjectModal] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState<string | null>(null);
  const [projectNameInput, setProjectNameInput] = useState("");
  const [projectPathInput, setProjectPathInput] = useState("");
  const [projectDescriptionInput, setProjectDescriptionInput] = useState("");
  const [projectTagsInput, setProjectTagsInput] = useState("");

  const runtimeSummary = useMemo(
    () => summarizeRuntimeOverview(counts, providers, models),
    [counts, providers, models]
  );
  const securitySummary = useMemo(
    () => summarizeSecurityWidget(overview, alerts, findings, systemHealth),
    [overview, alerts, findings, systemHealth]
  );
  const systemStatusModel = useMemo(
    () =>
      buildHomeSystemStatus({
        securitySummary,
        runtimeSummary,
        securityLoading,
        providersLoading,
        securityError,
        providersError,
        partialData,
        missingSources,
      }),
    [
      missingSources,
      partialData,
      providersError,
      providersLoading,
      runtimeSummary,
      securityError,
      securityLoading,
      securitySummary,
    ]
  );

  const projectNameById = useMemo(() => {
    const map = new Map<string, string>();
    projects.forEach((project) => {
      map.set(project.project_id, project.name || project.project_id);
    });
    return map;
  }, [projects]);

  const refreshRecentThreads = useCallback(() => {
    if (typeof window === "undefined") {
      setRecentThreads([]);
      return;
    }

    try {
      const raw = localStorage.getItem(THREADS_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      setRecentThreads(extractRecentThreads(parsed, 8));
    } catch {
      setRecentThreads([]);
    }
  }, []);

  useEffect(() => {
    refreshRecentThreads();
    const interval = window.setInterval(refreshRecentThreads, 15000);
    const onStorage = (event: StorageEvent) => {
      if (event.key === THREADS_STORAGE_KEY) {
        refreshRecentThreads();
      }
    };

    window.addEventListener("storage", onStorage);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("storage", onStorage);
    };
  }, [refreshRecentThreads]);

  const refreshAllWidgets = useCallback(async () => {
    refreshRecentThreads();
    await Promise.all([refreshProjects(), refreshProjectContext(), refreshProviders(), refreshSecurity()]);
  }, [refreshProjectContext, refreshProjects, refreshProviders, refreshRecentThreads, refreshSecurity]);

  const openProjectInPanel = useCallback(
    async (panel: "chat" | "workbench") => {
      if (!selectedProjectId) {
        return;
      }
      await openProject(selectedProjectId);
      setActivePanel(panel);
    },
    [openProject, selectedProjectId, setActivePanel]
  );

  const openRecentThread = useCallback(
    (threadId: string) => {
      if (typeof window === "undefined") {
        return;
      }

      try {
        const raw = localStorage.getItem(THREADS_STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : null;
        const updated = markThreadActive(parsed, threadId);
        localStorage.setItem(THREADS_STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Ignore local persistence errors and still switch panels.
      }

      setActivePanel("chat");
    },
    [setActivePanel]
  );

  const createProject = useCallback(async () => {
    // Frontend validation - align with backend contract
    if (!projectPathInput) {
      setProjectCreateError("Project path is required.");
      return;
    }

    if (!projectPathInput.startsWith('/')) {
      setProjectCreateError("Project path must be an absolute path starting with /");
      return;
    }

    if (projectPathInput.length < 3) {
      setProjectCreateError("Project path is too short");
      return;
    }

    // Check for common invalid paths based on backend safety rules
    const invalidPatterns = ['/usr', '/boot', '/ostree', '/var/home/lch/projects/bazzite-laptop']; // Add repo root as invalid
    const isInInvalidLocation = invalidPatterns.some(pattern => 
      projectPathInput.startsWith(pattern) && projectPathInput !== pattern
    );
    if (isInInvalidLocation) {
      setProjectCreateError("Cannot create project in system directories or the agent repository itself.");
      return;
    }

    let finalProjectName = projectNameInput.trim();
    if (!finalProjectName && !projectPathInput.endsWith('/')) {
        // If no name is provided, try to infer from path, but only if path is not just a directory separator
        const pathParts = projectPathInput.split('/').filter(Boolean);
        if (pathParts.length > 0) {
            finalProjectName = pathParts[pathParts.length - 1];
        }
    }
    if (!finalProjectName) {
        setProjectCreateError("Project name or a valid path to infer name from is required.");
        return;
    }

    const payload = buildProjectRegisterArgs({
      name: finalProjectName,
      path: projectPathInput,
      description: projectDescriptionInput,
      tags: projectTagsInput,
    });

    setProjectCreateError(null);
    setIsCreatingProject(true);

    try {
      const response = (await callMCPTool("workbench.project_register", payload)) as ProjectRegisterResponse;
      if (response.success === false || !response.project?.project_id) {
        setProjectCreateError(response.error || "Project registration failed.");
        return;
      }

      await refreshProjects();
      setSelectedProjectId(response.project.project_id);
      await openProject(response.project.project_id);

      setProjectNameInput("");
      setProjectPathInput("");
      setProjectDescriptionInput("");
      setProjectTagsInput("");
      setShowCreateProjectModal(false);
    } catch (error) {
      setProjectCreateError(
        error instanceof Error ? error.message : "Project registration failed."
      );
    } finally {
      setIsCreatingProject(false);
    }
  }, [
    openProject,
    projectDescriptionInput,
    projectNameInput,
    projectPathInput,
    projectTagsInput,
    refreshProjects,
    setSelectedProjectId,
  ]);

  return (
    <div className="h-full overflow-auto px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
            Home Dashboard
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            Live system view for project entry, runtime health, security, and recent work.
          </p>
        </div>
        <button
          onClick={() => {
            void refreshAllWidgets();
          }}
          className="px-4 py-2 rounded-lg text-sm"
          style={{
            background: "var(--base-02)",
            color: "var(--text-primary)",
            border: "1px solid var(--base-04)",
          }}
        >
          Refresh Widgets
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <HomeCard title="Active Project" subtitle="Project context and launch controls">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 items-center">
              <select
                value={selectedProjectId || ""}
                onChange={(event) => setSelectedProjectId(event.target.value || null)}
                className="flex-1 min-w-[220px] px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--base-01)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--base-04)",
                }}
              >
                <option value="">Select project</option>
                {projects.map((project) => (
                  <option key={project.project_id} value={project.project_id}>
                    {project.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => setShowCreateProjectModal(true)}
                className="px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--base-02)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--base-04)",
                }}
              >
                Register Project
              </button>
            </div>

            {selectedProject ? (
              <div
                className="rounded-lg px-3 py-2"
                style={{
                  background: "var(--base-01)",
                  border: "1px solid var(--base-04)",
                  color: "var(--text-secondary)",
                }}
              >
                <div className="font-medium" style={{ color: "var(--text-primary)" }}>
                  {selectedProject.name}
                </div>
                <div className="text-xs mt-1 truncate" title={selectedProject.root_path}>
                  {selectedProject.root_path}
                </div>
                <div className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
                  Updated {formatRelativeTime(selectedProject.updated_at)}
                </div>
              </div>
            ) : (
              <div className="text-sm px-3 py-2 rounded-lg" style={{ background: "var(--base-01)", border: "1px solid var(--base-04)", color: "var(--text-secondary)" }}>
                Select a project to launch Chat/Workbench with bound context.
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => {
                  void openProjectInPanel("chat");
                }}
                disabled={!selectedProjectId}
                className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-50"
                style={{ background: "var(--accent-primary)", color: "white" }}
              >
                Open in Chat
              </button>
              <button
                onClick={() => {
                  void openProjectInPanel("workbench");
                }}
                disabled={!selectedProjectId}
                className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-50"
                style={{
                  background: "var(--base-02)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--base-04)",
                }}
              >
                Open in Workbench
              </button>
            </div>

            <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
              {isLoadingProjects
                ? "Loading projects..."
                : `${projects.length} registered project${projects.length === 1 ? "" : "s"}`}
              {workbenchError ? ` · ${workbenchError}` : ""}
            </div>
          </div>
        </HomeCard>

        <HomeCard title="Recent Threads" subtitle="Continue recent local chat work">
          {recentThreads.length === 0 ? (
            <div className="text-sm px-3 py-2 rounded-lg" style={{ background: "var(--base-01)", border: "1px solid var(--base-04)", color: "var(--text-secondary)" }}>
              No recent threads yet. Open Chat Workspace to start one.
            </div>
          ) : (
            <div className="space-y-2">
              {recentThreads.slice(0, 6).map((thread) => (
                <button
                  key={thread.id}
                  onClick={() => openRecentThread(thread.id)}
                  className="w-full text-left rounded-lg px-3 py-2 transition-colors hover:bg-base-01"
                  style={{ border: "1px solid var(--base-04)" }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm truncate" style={{ color: "var(--text-primary)" }}>
                      {thread.title}
                    </span>
                    <span className="text-xs shrink-0" style={{ color: "var(--text-tertiary)" }}>
                      {formatRelativeTime(thread.updatedAt)}
                    </span>
                  </div>
                  <div className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                    {(projectNameById.get(thread.projectId) || "Unassigned")}{thread.folderPath && ` / ${thread.folderPath}`} · {thread.mode}
                    {thread.isPinned ? " · pinned" : ""}
                  </div>
                </button>
              ))}
            </div>
          )}
        </HomeCard>

        <HomeCard title="System Status" subtitle="Condensed live security + runtime health">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                {systemStatusModel.title}
              </span>
              <span
                className="px-2 py-1 rounded text-xs"
                style={{
                  background: "var(--base-01)",
                  border: "1px solid var(--base-04)",
                  color:
                    systemStatusModel.tone === "danger"
                      ? "var(--danger)"
                      : systemStatusModel.tone === "warning"
                        ? "var(--warning)"
                        : systemStatusModel.tone === "success"
                          ? "var(--success)"
                          : "var(--text-secondary)",
                }}
              >
                {securitySummary.status}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <MetricChip label="Critical" value={securitySummary.critical} tone="danger" />
              <MetricChip label="Alerts" value={securitySummary.alerts} tone="warning" />
              <MetricChip label="Healthy" value={runtimeSummary.healthy} tone="success" />
              <MetricChip label="Degraded" value={runtimeSummary.degraded + runtimeSummary.blocked} tone="warning" />
            </div>
            <div className="space-y-1">
              {systemStatusModel.details.slice(0, 3).map((line) => (
                <p key={line} className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                  {line}
                </p>
              ))}
            </div>
          </div>
        </HomeCard>

        <HomeCard title="Quick Actions" subtitle="Jump directly into focused operator surfaces">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <QuickAction label="Chat Workspace" onClick={() => setActivePanel("chat")} />
            <QuickAction label="Security Ops" onClick={() => setActivePanel("security")} />
            <QuickAction label="Tools" onClick={() => setActivePanel("tools")} />
            <QuickAction label="Providers" onClick={() => setActivePanel("models")} />
            <QuickAction label="Projects" onClick={() => setActivePanel("projects")} />
            <QuickAction label="Workbench" onClick={() => setActivePanel("workbench")} />
          </div>
          {(context?.current_phase?.phase_number || context?.current_phase?.phase_name) && (
            <p className="mt-3 text-xs" style={{ color: "var(--text-tertiary)" }}>
              Active phase: {context?.current_phase?.phase_number || "unknown"} · {context?.current_phase?.phase_name || "unknown"}
            </p>
          )}
        </HomeCard>
      </div>

      {showCreateProjectModal && (
        <ModalFrame title="Register Project" onClose={() => setShowCreateProjectModal(false)}>
          <div className="grid grid-cols-1 gap-2">
            <input
              value={projectNameInput}
              onChange={(event) => setProjectNameInput(event.target.value)}
              placeholder="Project name"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--base-01)",
                color: "var(--text-primary)",
                border: "1px solid var(--base-04)",
              }}
            />
            <input
              value={projectPathInput}
              onChange={(event) => setProjectPathInput(event.target.value)}
              placeholder="/absolute/path/to/project"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--base-01)",
                color: "var(--text-primary)",
                border: "1px solid var(--base-04)",
              }}
            />
            <input
              value={projectDescriptionInput}
              onChange={(event) => setProjectDescriptionInput(event.target.value)}
              placeholder="Description (optional)"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--base-01)",
                color: "var(--text-primary)",
                border: "1px solid var(--base-04)",
              }}
            />
            <input
              value={projectTagsInput}
              onChange={(event) => setProjectTagsInput(event.target.value)}
              placeholder="tag1, tag2"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--base-01)",
                color: "var(--text-primary)",
                border: "1px solid var(--base-04)",
              }}
            />
            {projectCreateError && (
              <span className="text-xs" style={{ color: "var(--danger)" }}>
                {projectCreateError}
              </span>
            )}
            <div className="flex items-center gap-2 mt-1">
              <button
                onClick={() => {
                  void createProject();
                }}
                disabled={isCreatingProject}
                className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-50"
                style={{ background: "var(--success)", color: "white" }}
              >
                {isCreatingProject ? "Creating..." : "Create Project"}
              </button>
              <button
                onClick={() => setShowCreateProjectModal(false)}
                className="px-3 py-1.5 rounded-lg text-sm"
                style={{
                  background: "var(--base-02)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--base-04)",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </ModalFrame>
      )}
    </div>
  );
}

function HomeCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section
      className="rounded-xl p-4"
      style={{
        background: "var(--base-02)",
        border: "1px solid var(--base-04)",
      }}
    >
      <div className="mb-3">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </h3>
        <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
          {subtitle}
        </p>
      </div>
      {children}
    </section>
  );
}

function MetricChip({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "success" | "warning" | "danger" | "neutral";
}) {
  const colorByTone = {
    success: "var(--success)",
    warning: "var(--warning)",
    danger: "var(--danger)",
    neutral: "var(--text-secondary)",
  };

  return (
    <div
      className="rounded-lg px-3 py-2"
      style={{
        border: "1px solid var(--base-04)",
        background: "var(--base-01)",
      }}
    >
      <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
        {label}
      </div>
      <div className="text-base font-semibold" style={{ color: colorByTone[tone] }}>
        {value}
      </div>
    </div>
  );
}

function QuickAction({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-01"
      style={{
        border: "1px solid var(--base-04)",
        color: "var(--text-primary)",
      }}
    >
      {label}
    </button>
  );
}

function ModalFrame({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0, 0, 0, 0.45)" }}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="w-full max-w-lg rounded-xl p-4"
        style={{
          background: "var(--base-02)",
          border: "1px solid var(--base-04)",
          boxShadow: "var(--shadow-xl)",
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h4>
          <button
            onClick={onClose}
            className="px-2 py-1 rounded text-xs"
            style={{
              background: "var(--base-01)",
              color: "var(--text-secondary)",
              border: "1px solid var(--base-04)",
            }}
          >
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
