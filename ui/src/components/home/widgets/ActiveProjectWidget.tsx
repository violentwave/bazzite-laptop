"use client";

import { useCallback, useEffect, useState } from "react";
import { useAgentWorkbench } from "@/hooks/useAgentWorkbench";
import { WidgetContainer } from "./WidgetContainer";
import { CHAT_SELECTED_PROJECT_KEY } from "@/lib/home-dashboard";
import { WorkbenchProject } from "@/types/agent-workbench";
import { callMCPTool } from "@/lib/mcp-client";

type ActiveProjectWidgetProps = {
  onProjectSelect?: (projectId: string) => void;
  onOpenInChat?: (projectId: string) => void;
  onOpenInWorkbench?: (projectId: string) => void;
  onRemove?: () => void;
};

type ProjectRegisterResponse = {
  success?: boolean;
  project?: WorkbenchProject;
  error?: string;
};

export function ActiveProjectWidget({
  onProjectSelect,
  onOpenInChat,
  onOpenInWorkbench,
  onRemove,
}: ActiveProjectWidgetProps = {}) {
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
  const [showCreateProjectModal, setShowCreateProjectModal] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState<string | null>(null);
  const [projectNameInput, setProjectNameInput] = useState("");
  const [projectPathInput, setProjectPathInput] = useState("");
  const [projectDescriptionInput, setProjectDescriptionInput] = useState("");
  const [projectTagsInput, setProjectTagsInput] = useState("");

  const formatRelativeTime = useCallback((timestamp: string): string => {
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
  }, []);

  useEffect(() => {
    if (selectedProjectId && onProjectSelect) {
      onProjectSelect(selectedProjectId);
    }
  }, [selectedProjectId, onProjectSelect]);

  const openProjectInPanel = useCallback(
    async (panel: "chat" | "workbench") => {
      if (!selectedProjectId) {
        return;
      }
      await openProject(selectedProjectId);
      if (typeof window !== "undefined") {
        localStorage.setItem(CHAT_SELECTED_PROJECT_KEY, selectedProjectId);
      }
      if (panel === "chat" && onOpenInChat) {
        onOpenInChat(selectedProjectId);
      }
      if (panel === "workbench" && onOpenInWorkbench) {
        onOpenInWorkbench(selectedProjectId);
      }
    },
    [openProject, selectedProjectId, onOpenInChat, onOpenInWorkbench]
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
    const invalidPatterns = ['/usr', '/boot', '/ostree', '/var/home/lch/projects/bazzite-laptop'];
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

    const payload = {
      name: finalProjectName,
      path: projectPathInput,
      description: projectDescriptionInput,
      tags: projectTagsInput,
    };

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
      if (typeof window !== "undefined") {
        localStorage.setItem(CHAT_SELECTED_PROJECT_KEY, response.project.project_id);
      }

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

  if (isLoadingProjects) {
    return (
      <WidgetContainer
        title="Active Project"
        subtitle="Project context and launch controls"
        onRemove={onRemove}
      >
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </WidgetContainer>
    );
  }

  return (
    <WidgetContainer 
      title="Active Project" 
      subtitle="Project context and launch controls"
      onRemove={onRemove}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 items-center">
          <select
            value={selectedProjectId || ""}
            onChange={(event) => setSelectedProjectId(event.target.value || null)}
            className="flex-1 min-w-[220px] px-3 py-2 rounded-lg border border-base-4 text-sm bg-base-1 text-primary"
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
            className="px-3 py-2 rounded-lg border border-base-4 text-sm bg-base-2 text-primary hover:bg-base-1"
          >
            Register Project
          </button>
        </div>

        {selectedProject ? (
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="font-medium text-primary">
              {selectedProject.name}
            </div>
            <div className="text-xs mt-1 truncate title-tooltip" title={selectedProject.root_path}>
              {selectedProject.root_path}
            </div>
            <div className="text-xs mt-1 text-tertiary">
              Updated {formatRelativeTime(selectedProject.updated_at)}
            </div>
          </div>
        ) : (
          <div className="text-sm px-3 py-2 rounded-lg border border-base-4 bg-base-1 text-tertiary">
            Select a project to launch Chat/Workbench with bound context.
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => {
              void openProjectInPanel("chat");
            }}
            disabled={!selectedProjectId}
            className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-50 bg-accent-primary text-white"
          >
            Open in Chat
          </button>
          <button
            onClick={() => {
              void openProjectInPanel("workbench");
            }}
            disabled={!selectedProjectId}
            className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-50 bg-base-2 text-primary border border-base-4 hover:bg-base-1"
          >
            Open in Workbench
          </button>
        </div>

        <div className="text-xs text-tertiary">
          {isLoadingProjects
            ? "Loading projects..."
            : `${projects.length} registered project${projects.length === 1 ? "" : "s"}`}
          {workbenchError ? ` · ${workbenchError}` : ""}
        </div>
      </div>

      {showCreateProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0, 0, 0, 0.45)" }} onClick={(event) => {
          if (event.target === event.currentTarget) {
            setShowCreateProjectModal(false);
          }
        }}>
          <div className="w-full max-w-lg rounded-xl p-4 border border-base-4 bg-base-2 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-primary">Register Project</h4>
              <button
                onClick={() => setShowCreateProjectModal(false)}
                className="px-2 py-1 rounded text-xs text-tertiary bg-base-1 border border-base-4 hover:bg-base-1"
              >
                Close
              </button>
            </div>
            <div className="grid grid-cols-1 gap-2">
              <p className="text-xs text-tertiary">
                Use an absolute path. System directories and the agent repository root are blocked.
              </p>
              <input
                value={projectNameInput}
                onChange={(event) => setProjectNameInput(event.target.value)}
                placeholder="Project name"
                className="w-full px-3 py-2 rounded-lg text-sm bg-base-1 text-primary border border-base-4"
              />
              <input
                value={projectPathInput}
                onChange={(event) => setProjectPathInput(event.target.value)}
                placeholder="/absolute/path/to/project"
                className="w-full px-3 py-2 rounded-lg text-sm bg-base-1 text-primary border border-base-4"
              />
              <input
                value={projectDescriptionInput}
                onChange={(event) => setProjectDescriptionInput(event.target.value)}
                placeholder="Description (optional)"
                className="w-full px-3 py-2 rounded-lg text-sm bg-base-1 text-primary border border-base-4"
              />
              <input
                value={projectTagsInput}
                onChange={(event) => setProjectTagsInput(event.target.value)}
                placeholder="tag1, tag2"
                className="w-full px-3 py-2 rounded-lg text-sm bg-base-1 text-primary border border-base-4"
              />
              {projectCreateError && (
                <span className="text-xs text-danger">
                  {projectCreateError}
                </span>
              )}
              <div className="flex items-center gap-2 mt-1">
                <button
                  onClick={() => {
                    void createProject();
                  }}
                  disabled={isCreatingProject}
                  className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-50 bg-success text-white"
                >
                  {isCreatingProject ? "Creating..." : "Create Project"}
                </button>
                <button
                  onClick={() => setShowCreateProjectModal(false)}
                  className="px-3 py-1.5 rounded-lg text-sm bg-base-2 text-primary border border-base-4 hover:bg-base-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </WidgetContainer>
  );
}
