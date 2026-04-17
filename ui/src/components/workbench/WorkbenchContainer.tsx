"use client";

import { useEffect } from "react";
import { AgentSelector } from "./AgentSelector";
import { GitStatusPanel } from "./GitStatusPanel";
import { HandoffPanel } from "./HandoffPanel";
import { ProjectPicker } from "./ProjectPicker";
import { SessionPanel } from "./SessionPanel";
import { TestResultsPanel } from "./TestResultsPanel";
import { useAgentWorkbench } from "@/hooks/useAgentWorkbench";

export function WorkbenchContainer() {
  const {
    projects,
    selectedProject,
    selectedProjectId,
    projectStatus,
    sessions,
    selectedSessionId,
    gitStatus,
    testCommands,
    testExecution,
    handoffNotes,
    profiles,
    selectedBackend,
    selectedSandboxProfile,
    leaseMinutes,
    isLoadingProjects,
    isLoadingSessions,
    isLoadingGit,
    isLoadingTests,
    isSavingHandoff,
    error,
    lastRefresh,
    setSelectedBackend,
    setSelectedSandboxProfile,
    setLeaseMinutes,
    refreshProjects,
    openProject,
    refreshSessions,
    createSession,
    attachSession,
    stopSession,
    refreshGitStatus,
    refreshTestCommands,
    runTestCommand,
    saveHandoffNote,
  } = useAgentWorkbench();

  useEffect(() => {
    if (selectedProjectId && !projectStatus) {
      void openProject(selectedProjectId);
    }
  }, [openProject, projectStatus, selectedProjectId]);

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--base-00)" }}>
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ background: "var(--base-01)", borderColor: "var(--base-04)" }}
      >
        <div>
          <h2 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            Agent Workbench
          </h2>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Project-scoped agent sessions, git/test visibility, and handoff closeout.
          </p>
        </div>
        <div
          className="px-2 py-1 rounded text-xs"
          style={{
            background: "var(--base-02)",
            color: error ? "var(--warning)" : "var(--success)",
            border: "1px solid var(--base-04)",
          }}
        >
          {error
            ? "degraded"
            : lastRefresh
            ? `updated ${lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
            : "ready"}
        </div>
      </div>

      {error && (
        <div
          className="mx-4 mt-3 rounded-lg border-l-2 p-3 text-xs"
          style={{
            borderColor: "var(--warning)",
            background: "rgba(245, 158, 11, 0.08)",
            color: "var(--text-secondary)",
          }}
        >
          MCP/workbench degraded: {error}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 xl:col-span-4 space-y-4">
            <ProjectPicker
              projects={projects}
              selectedProjectId={selectedProjectId}
              projectStatus={projectStatus}
              isLoading={isLoadingProjects}
              error={null}
              onRefresh={refreshProjects}
              onSelectProject={(projectId) => {
                if (projectId) {
                  void openProject(projectId);
                }
              }}
            />
            <AgentSelector
              profiles={profiles}
              selectedBackend={selectedBackend}
              selectedSandboxProfile={selectedSandboxProfile}
              leaseMinutes={leaseMinutes}
              onBackendChange={setSelectedBackend}
              onSandboxChange={setSelectedSandboxProfile}
              onLeaseChange={setLeaseMinutes}
            />
            <SessionPanel
              sessions={sessions}
              selectedSessionId={selectedSessionId}
              selectedProjectId={selectedProjectId}
              isLoading={isLoadingSessions}
              error={null}
              onRefresh={refreshSessions}
              onCreate={createSession}
              onAttach={attachSession}
              onStop={stopSession}
            />
          </div>

          <div className="col-span-12 xl:col-span-8 space-y-4">
            <div className="rounded-xl border p-4" style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}>
              <div className="text-sm" style={{ color: "var(--text-primary)" }}>
                Active project: {selectedProject ? selectedProject.name : "none selected"}
              </div>
              <div className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
                {selectedProject
                  ? `${selectedProject.project_id} · ${selectedProject.tags.join(", ") || "no tags"}`
                  : "Select a registered project to continue."}
              </div>
            </div>

            <GitStatusPanel
              gitStatus={gitStatus}
              isLoading={isLoadingGit}
              selectedProjectId={selectedProjectId}
              error={null}
              onRefresh={refreshGitStatus}
            />

            <TestResultsPanel
              selectedProjectId={selectedProjectId}
              commands={testCommands}
              execution={testExecution}
              isLoading={isLoadingTests}
              error={null}
              onRefresh={refreshTestCommands}
              onRun={runTestCommand}
            />

            <HandoffPanel
              selectedSessionId={selectedSessionId}
              notes={handoffNotes}
              isSaving={isSavingHandoff}
              error={null}
              onSave={saveHandoffNote}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
