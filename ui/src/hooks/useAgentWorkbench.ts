"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { callMCPTool } from "@/lib/mcp-client";
import {
  WorkbenchAgentProfile,
  WorkbenchBackend,
  WorkbenchGitStatus,
  WorkbenchHandoffNote,
  WorkbenchProject,
  WorkbenchProjectStatus,
  WorkbenchSandboxProfile,
  WorkbenchSession,
  WorkbenchTestCommand,
  WorkbenchTestExecution,
} from "@/types/agent-workbench";

const AGENT_PROFILES: WorkbenchAgentProfile[] = [
  {
    id: "opencode",
    label: "OpenCode",
    mode: "bounded",
    shell_access: false,
    network_access: false,
    allowed_tools: ["workbench.*", "project.*", "code.*", "knowledge.*", "memory.search"],
    notes: "Default local profile for bounded task execution.",
  },
  {
    id: "codex",
    label: "Codex",
    mode: "bounded",
    shell_access: false,
    network_access: false,
    allowed_tools: ["workbench.*", "project.*", "code.*", "knowledge.*", "memory.search"],
    notes: "Bounded coding profile with manual approval semantics.",
  },
  {
    id: "claude-code",
    label: "Claude Code",
    mode: "bounded",
    shell_access: false,
    network_access: false,
    allowed_tools: ["workbench.*", "project.*", "code.*", "knowledge.*", "memory.search"],
    notes: "Bounded operator profile; no unrestricted daemon or shell access.",
  },
  {
    id: "gemini-cli",
    label: "Gemini CLI",
    mode: "bounded",
    shell_access: false,
    network_access: false,
    allowed_tools: ["workbench.*", "project.*", "code.*", "knowledge.*", "memory.search"],
    notes: "Bounded analysis profile with controlled MCP tool scope.",
  },
];

type ToolErrorPayload = {
  success?: boolean;
  error?: string;
  error_code?: string;
};

function asToolError(payload: unknown): ToolErrorPayload | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const typed = payload as ToolErrorPayload;
  if (typed.success === false) {
    return typed;
  }
  return null;
}

function formatToolError(tool: string, payload: unknown): string {
  const parsed = asToolError(payload);
  if (parsed) {
    return `${tool}: ${parsed.error || parsed.error_code || "request failed"}`;
  }
  return `${tool}: unavailable`;
}

interface UseAgentWorkbenchReturn {
  projects: WorkbenchProject[];
  selectedProjectId: string | null;
  selectedProject: WorkbenchProject | null;
  projectStatus: WorkbenchProjectStatus | null;
  sessions: WorkbenchSession[];
  selectedSessionId: string | null;
  selectedSession: WorkbenchSession | null;
  gitStatus: WorkbenchGitStatus | null;
  testCommands: WorkbenchTestCommand[];
  testExecution: WorkbenchTestExecution | null;
  handoffNotes: WorkbenchHandoffNote[];
  profiles: WorkbenchAgentProfile[];
  selectedBackend: WorkbenchBackend;
  selectedSandboxProfile: WorkbenchSandboxProfile;
  leaseMinutes: number;
  isLoadingProjects: boolean;
  isLoadingSessions: boolean;
  isLoadingGit: boolean;
  isLoadingTests: boolean;
  isSavingHandoff: boolean;
  error: string | null;
  lastRefresh: Date | null;
  setSelectedProjectId: (projectId: string | null) => void;
  setSelectedSessionId: (sessionId: string | null) => void;
  setSelectedBackend: (backend: WorkbenchBackend) => void;
  setSelectedSandboxProfile: (profile: WorkbenchSandboxProfile) => void;
  setLeaseMinutes: (minutes: number) => void;
  refreshProjects: () => Promise<void>;
  openProject: (projectId: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
  createSession: () => Promise<void>;
  attachSession: (sessionId: string) => Promise<void>;
  stopSession: (sessionId: string) => Promise<void>;
  refreshGitStatus: () => Promise<void>;
  refreshTestCommands: () => Promise<void>;
  runTestCommand: (commandName: string) => Promise<void>;
  saveHandoffNote: (summary: string, artifacts: string[], phase: string) => Promise<void>;
}

export function useAgentWorkbench(): UseAgentWorkbenchReturn {
  const [projects, setProjects] = useState<WorkbenchProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [projectStatus, setProjectStatus] = useState<WorkbenchProjectStatus | null>(null);
  const [sessions, setSessions] = useState<WorkbenchSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [gitStatus, setGitStatus] = useState<WorkbenchGitStatus | null>(null);
  const [testCommands, setTestCommands] = useState<WorkbenchTestCommand[]>([]);
  const [testExecution, setTestExecution] = useState<WorkbenchTestExecution | null>(null);
  const [handoffNotes, setHandoffNotes] = useState<WorkbenchHandoffNote[]>([]);
  const [selectedBackend, setSelectedBackend] = useState<WorkbenchBackend>("opencode");
  const [selectedSandboxProfile, setSelectedSandboxProfile] =
    useState<WorkbenchSandboxProfile>("conservative");
  const [leaseMinutes, setLeaseMinutes] = useState<number>(60);
  const [isLoadingProjects, setIsLoadingProjects] = useState<boolean>(true);
  const [isLoadingSessions, setIsLoadingSessions] = useState<boolean>(false);
  const [isLoadingGit, setIsLoadingGit] = useState<boolean>(false);
  const [isLoadingTests, setIsLoadingTests] = useState<boolean>(false);
  const [isSavingHandoff, setIsSavingHandoff] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const openingProjectRef = useRef<string | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) || null,
    [projects, selectedProjectId]
  );

  const selectedSession = useMemo(
    () => sessions.find((session) => session.session_id === selectedSessionId) || null,
    [sessions, selectedSessionId]
  );

  const refreshProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setError(null);
    try {
      const payload = (await callMCPTool("workbench.project_list")) as {
        success?: boolean;
        projects?: WorkbenchProject[];
        error?: string;
      };

      if (payload.success === false) {
        setError(formatToolError("workbench.project_list", payload));
        setProjects([]);
        return;
      }

      const nextProjects = payload.projects || [];
      setProjects(nextProjects);

      setSelectedProjectId((previous) => {
        if (previous && nextProjects.some((item) => item.project_id === previous)) {
          return previous;
        }
        const firstProject = nextProjects[0]?.project_id || null;
        setSelectedSessionId(null);
        if (!firstProject) {
          setProjectStatus(null);
          setSessions([]);
          setGitStatus(null);
          setTestCommands([]);
          setTestExecution(null);
        }
        return firstProject;
      });

      setLastRefresh(new Date());
    } catch (err) {
      setError(
        err instanceof Error
          ? `Agent Workbench unavailable: ${err.message}`
          : "Agent Workbench unavailable"
      );
      setProjects([]);
    } finally {
      setIsLoadingProjects(false);
    }
  }, []);

  const refreshSessions = useCallback(async () => {
    if (!selectedProjectId) {
      setSessions([]);
      return;
    }
    setIsLoadingSessions(true);
    try {
      const payload = (await callMCPTool("workbench.session_list", {
        project_id: selectedProjectId,
      })) as {
        success?: boolean;
        sessions?: WorkbenchSession[];
      };

      if (payload.success === false) {
        setError(formatToolError("workbench.session_list", payload));
        setSessions([]);
        return;
      }

      const nextSessions = payload.sessions || [];
      setSessions(nextSessions);
      if (!nextSessions.some((item) => item.session_id === selectedSessionId)) {
        setSelectedSessionId(nextSessions[0]?.session_id || null);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? `Session list failed: ${err.message}`
          : "Session list failed"
      );
      setSessions([]);
    } finally {
      setIsLoadingSessions(false);
    }
  }, [selectedProjectId, selectedSessionId]);

  const refreshGitStatus = useCallback(async () => {
    if (!selectedProjectId) {
      setGitStatus(null);
      return;
    }
    setIsLoadingGit(true);
    try {
      const payload = (await callMCPTool("workbench.git_status", {
        project_id: selectedProjectId,
      })) as {
        success?: boolean;
        git?: WorkbenchGitStatus;
      };

      if (payload.success === false) {
        setError(formatToolError("workbench.git_status", payload));
        setGitStatus(null);
        return;
      }

      setGitStatus(payload.git || null);
    } catch (err) {
      setError(
        err instanceof Error ? `Git status failed: ${err.message}` : "Git status failed"
      );
      setGitStatus(null);
    } finally {
      setIsLoadingGit(false);
    }
  }, [selectedProjectId]);

  const refreshTestCommands = useCallback(async () => {
    if (!selectedProjectId) {
      setTestCommands([]);
      return;
    }
    setIsLoadingTests(true);
    try {
      const payload = (await callMCPTool("workbench.test_commands", {
        project_id: selectedProjectId,
      })) as {
        success?: boolean;
        commands?: WorkbenchTestCommand[];
      };

      if (payload.success === false) {
        setError(formatToolError("workbench.test_commands", payload));
        setTestCommands([]);
        return;
      }

      setTestCommands(payload.commands || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? `Test command discovery failed: ${err.message}`
          : "Test command discovery failed"
      );
      setTestCommands([]);
    } finally {
      setIsLoadingTests(false);
    }
  }, [selectedProjectId]);

  const openProject = useCallback(async (projectId: string) => {
    if (openingProjectRef.current === projectId) {
      return;
    }
    openingProjectRef.current = projectId;
    setError(null);
    setSelectedProjectId(projectId);
    setSelectedSessionId(null);
    try {
      const [opened, statusPayload] = (await Promise.all([
        callMCPTool("workbench.project_open", { project_id: projectId }),
        callMCPTool("workbench.project_status", { project_id: projectId }),
      ])) as [
        { success?: boolean; project?: WorkbenchProject },
        { success?: boolean } & WorkbenchProjectStatus
      ];

      if (opened.success === false) {
        setError(formatToolError("workbench.project_open", opened));
      }

      if (statusPayload.success === false) {
        setError(formatToolError("workbench.project_status", statusPayload));
        setProjectStatus(null);
      } else {
        setProjectStatus(statusPayload);
      }

      await Promise.all([refreshSessions(), refreshGitStatus(), refreshTestCommands()]);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? `Project open failed: ${err.message}` : "Project open failed");
      setProjectStatus(null);
    } finally {
      if (openingProjectRef.current === projectId) {
        openingProjectRef.current = null;
      }
    }
  }, [refreshGitStatus, refreshSessions, refreshTestCommands]);

  const createSession = useCallback(async () => {
    if (!selectedProjectId) {
      setError("Select a project before creating a session");
      return;
    }
    setIsLoadingSessions(true);
    try {
      const payload = (await callMCPTool("workbench.session_create", {
        project_id: selectedProjectId,
        backend: selectedBackend,
        sandbox_profile: selectedSandboxProfile,
        lease_minutes: leaseMinutes,
      })) as { success?: boolean; session?: WorkbenchSession };

      if (payload.success === false) {
        setError(formatToolError("workbench.session_create", payload));
        return;
      }

      if (payload.session?.session_id) {
        setSelectedSessionId(payload.session.session_id);
      }
      await refreshSessions();
      setLastRefresh(new Date());
    } catch (err) {
      setError(
        err instanceof Error ? `Session create failed: ${err.message}` : "Session create failed"
      );
    } finally {
      setIsLoadingSessions(false);
    }
  }, [leaseMinutes, refreshSessions, selectedBackend, selectedProjectId, selectedSandboxProfile]);

  const attachSession = useCallback(async (sessionId: string) => {
    try {
      const payload = (await callMCPTool("workbench.session_get", {
        session_id: sessionId,
      })) as { success?: boolean; session?: WorkbenchSession };

      if (payload.success === false) {
        setError(formatToolError("workbench.session_get", payload));
        return;
      }

      if (payload.session) {
        setSelectedSessionId(payload.session.session_id);
      }
    } catch (err) {
      setError(
        err instanceof Error ? `Session attach failed: ${err.message}` : "Session attach failed"
      );
    }
  }, []);

  const stopSession = useCallback(async (sessionId: string) => {
    try {
      const payload = (await callMCPTool("workbench.session_stop", {
        session_id: sessionId,
      })) as { success?: boolean };

      if (payload.success === false) {
        setError(formatToolError("workbench.session_stop", payload));
        return;
      }

      await refreshSessions();
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
      }
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? `Session stop failed: ${err.message}` : "Session stop failed");
    }
  }, [refreshSessions, selectedSessionId]);

  const runTestCommand = useCallback(async (commandName: string) => {
    if (!selectedProjectId) {
      setError("Select a project before running tests");
      return;
    }
    setIsLoadingTests(true);
    try {
      const payload = (await callMCPTool("workbench.test_commands", {
        project_id: selectedProjectId,
        command_name: commandName,
        execute: true,
      })) as { success?: boolean; execution?: WorkbenchTestExecution };

      if (payload.success === false) {
        setError(formatToolError("workbench.test_commands", payload));
        return;
      }

      setTestExecution(payload.execution || null);
      setLastRefresh(new Date());
      await refreshTestCommands();
    } catch (err) {
      setError(
        err instanceof Error
          ? `Test execution failed: ${err.message}`
          : "Test execution failed"
      );
    } finally {
      setIsLoadingTests(false);
    }
  }, [refreshTestCommands, selectedProjectId]);

  const saveHandoffNote = useCallback(
    async (summary: string, artifacts: string[], phase: string) => {
      setIsSavingHandoff(true);
      try {
        const payload = (await callMCPTool("workbench.handoff_note", {
          summary,
          artifacts: artifacts.join(","),
          phase,
          session_id: selectedSessionId || undefined,
        })) as { success?: boolean; note?: WorkbenchHandoffNote };

        if (payload.success === false) {
          setError(formatToolError("workbench.handoff_note", payload));
          return;
        }

        if (payload.note) {
          setHandoffNotes((prev) => [payload.note as WorkbenchHandoffNote, ...prev].slice(0, 20));
        }
        setLastRefresh(new Date());
      } catch (err) {
        setError(
          err instanceof Error ? `Handoff save failed: ${err.message}` : "Handoff save failed"
        );
      } finally {
        setIsSavingHandoff(false);
      }
    },
    [selectedSessionId]
  );

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  return {
    projects,
    selectedProjectId,
    selectedProject,
    projectStatus,
    sessions,
    selectedSessionId,
    selectedSession,
    gitStatus,
    testCommands,
    testExecution,
    handoffNotes,
    profiles: AGENT_PROFILES,
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
    setSelectedProjectId,
    setSelectedSessionId,
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
  };
}
