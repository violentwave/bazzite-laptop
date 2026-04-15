"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  ShellSession,
  SessionContext,
  CommandResult,
  AuditLogEntry,
  SessionStatus,
  TerminalOutput,
} from "@/types/shell";
import { callMCPTool } from "@/lib/mcp-client";

const SHELL_ACTIVE_SESSION_KEY = "bazzite.shell.activeSessionId";

interface UseShellSessionsReturn {
  sessions: ShellSession[];
  activeSession: ShellSession | null;
  sessionContext: SessionContext | null;
  output: TerminalOutput[];
  isLoading: boolean;
  error: string | null;
  createSession: (name?: string, cwd?: string) => Promise<ShellSession>;
  executeCommand: (sessionId: string, command: string) => Promise<CommandResult>;
  terminateSession: (sessionId: string) => Promise<boolean>;
  setActiveSession: (session: ShellSession | null) => void;
  refreshSessions: () => Promise<void>;
  getAuditLog: (sessionId?: string, limit?: number) => Promise<AuditLogEntry[]>;
}

function isErrorResponse(data: unknown): data is { error: string; error_detail?: string; operator_action?: string } {
  return (
    typeof data === "object" &&
    data !== null &&
    "error" in data &&
    typeof (data as Record<string, unknown>).error === "string"
  );
}

function extractError(data: unknown, fallback: string): string {
  if (isErrorResponse(data)) {
    return data.error_detail || data.error || fallback;
  }
  return fallback;
}

export function useShellSessions(): UseShellSessionsReturn {
  const [sessions, setSessions] = useState<ShellSession[]>([]);
  const [activeSession, setActiveSessionRaw] = useState<ShellSession | null>(null);
  const [sessionContext, setSessionContext] = useState<SessionContext | null>(null);
  const [output, setOutput] = useState<TerminalOutput[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const outputRef = useRef<TerminalOutput[]>([]);

  const persistActiveSessionId = useCallback((sessionId: string | null) => {
    if (typeof window === "undefined") {
      return;
    }
    if (sessionId) {
      window.localStorage.setItem(SHELL_ACTIVE_SESSION_KEY, sessionId);
    } else {
      window.localStorage.removeItem(SHELL_ACTIVE_SESSION_KEY);
    }
  }, []);

  const getPersistedActiveSessionId = useCallback((): string | null => {
    if (typeof window === "undefined") {
      return null;
    }
    return window.localStorage.getItem(SHELL_ACTIVE_SESSION_KEY);
  }, []);

  const mergeSession = useCallback((updated: ShellSession) => {
    setSessions((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    setActiveSessionRaw((prev) => (prev?.id === updated.id ? updated : prev));
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      setError(null);
      const data = await callMCPTool("shell.list_sessions");
      if (Array.isArray(data)) {
        const sessionList = data as ShellSession[];
        setSessions(sessionList);
        setActiveSessionRaw((prev) => {
          const persistedId = getPersistedActiveSessionId();
          if (persistedId) {
            const persisted = sessionList.find((s) => s.id === persistedId);
            if (persisted) {
              return persisted;
            }
            persistActiveSessionId(null);
          }
          if (!prev) return null;
          const updated = sessionList.find((s) => s.id === prev.id);
          return updated || prev;
        });
      } else if (isErrorResponse(data)) {
        setError(extractError(data, "Failed to list sessions"));
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? `Shell unavailable: ${err.message}`
          : "Shell service unavailable"
      );
    }
  }, [getPersistedActiveSessionId, persistActiveSessionId]);

  const fetchSessionContext = useCallback(async (sessionId: string) => {
    try {
      const data = await callMCPTool("shell.get_context", { session_id: sessionId });
      if (isErrorResponse(data)) {
        console.warn("Session context error:", extractError(data, "Context unavailable"));
        setSessionContext(null);
        return;
      }
      if (data && typeof data === "object" && "session_id" in data) {
        setSessionContext(data as SessionContext);
      }
    } catch (err) {
      console.warn("Failed to fetch session context:", err);
      setSessionContext(null);
    }
  }, []);

  const createSession = useCallback(async (name?: string, cwd?: string): Promise<ShellSession> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await callMCPTool("shell.create_session", { name, cwd });
      if (isErrorResponse(data)) {
        const errMsg = extractError(data as Record<string, unknown>, "Failed to create session");
        setError(errMsg);
        throw new Error(errMsg);
      }
      const session = data as ShellSession;
      await refreshSessions();
      setActiveSessionRaw(session);
      persistActiveSessionId(session.id);

      const systemOutput: TerminalOutput = {
        type: "system",
        content: `Session created: ${session.name} (${session.id})`,
        timestamp: new Date().toISOString(),
      };
      outputRef.current = [systemOutput];
      setOutput(outputRef.current);

      if (session.status === "error") {
        setError(
          String(session.metadata?.error || "Session created in error state")
        );
        const errOutput: TerminalOutput = {
          type: "error",
          content: `Session error: ${String(session.metadata?.error || "unknown error")}`,
          timestamp: new Date().toISOString(),
        };
        outputRef.current = [...outputRef.current, errOutput];
        setOutput(outputRef.current);
      }

      return session;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create session";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [persistActiveSessionId, refreshSessions]);

  const executeCommand = useCallback(async (sessionId: string, command: string): Promise<CommandResult> => {
    setIsLoading(true);
    const commandOutput: TerminalOutput = {
      type: "input",
      content: `$ ${command}`,
      timestamp: new Date().toISOString(),
    };
    outputRef.current = [...outputRef.current, commandOutput];
    setOutput(outputRef.current);

    try {
      const data = await callMCPTool("shell.execute_command", {
        session_id: sessionId,
        command,
      });

      if (isErrorResponse(data)) {
        const errData = data as Record<string, unknown>;
        const errMsg = String(errData.error_detail || errData.error || "Command failed");
        const operatorAction = errData.operator_action
          ? ` ${String(errData.operator_action)}`
          : "";

        const errorOutput: TerminalOutput = {
          type: "error",
          content: `${errMsg}${operatorAction}`,
          timestamp: new Date().toISOString(),
        };
        outputRef.current = [...outputRef.current, errorOutput];
        setOutput(outputRef.current);

        return {
          success: false,
          error: String(errData.error),
          stderr: errMsg + operatorAction,
        } as CommandResult;
      }

      const result = data as CommandResult;

      if (result.stdout) {
        const stdoutOutput: TerminalOutput = {
          type: "output",
          content: result.stdout,
          timestamp: new Date().toISOString(),
        };
        outputRef.current = [...outputRef.current, stdoutOutput];
      }
      if (result.stderr) {
        const stderrOutput: TerminalOutput = {
          type: "error",
          content: result.stderr,
          timestamp: new Date().toISOString(),
        };
        outputRef.current = [...outputRef.current, stderrOutput];
      }
      if (!result.success && !result.stdout && !result.stderr && result.error) {
        const errorOutput: TerminalOutput = {
          type: "error",
          content: result.error,
          timestamp: new Date().toISOString(),
        };
        outputRef.current = [...outputRef.current, errorOutput];
      }
      setOutput(outputRef.current);

      await fetchSessionContext(sessionId);

      return result;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Command failed";
      const errorOutput: TerminalOutput = {
        type: "error",
        content: `Connection error: ${errMsg}`,
        timestamp: new Date().toISOString(),
      };
      outputRef.current = [...outputRef.current, errorOutput];
      setOutput(outputRef.current);

      return { success: false, error: errMsg } as CommandResult;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSessionContext]);

  const terminateSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      const data = await callMCPTool("shell.terminate_session", { session_id: sessionId });
      if (isErrorResponse(data)) {
        setError(extractError(data, "Failed to terminate session"));
        return false;
      }
      await refreshSessions();

      setActiveSessionRaw((prev) => {
        if (prev?.id === sessionId) return null;
        return prev;
      });
      if (activeSession?.id === sessionId) {
        setSessionContext(null);
        outputRef.current = [];
        setOutput([]);
        persistActiveSessionId(null);
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to terminate session");
      return false;
    }
  }, [activeSession, persistActiveSessionId, refreshSessions]);

  const getAuditLog = useCallback(async (sessionId?: string, limit?: number): Promise<AuditLogEntry[]> => {
    try {
      const data = await callMCPTool("shell.get_audit_log", { session_id: sessionId, limit });
      if (Array.isArray(data)) {
        return data as AuditLogEntry[];
      }
      return [];
    } catch (err) {
      console.warn("Failed to fetch audit log:", err);
      return [];
    }
  }, []);

  useEffect(() => {
    refreshSessions();
    const interval = setInterval(refreshSessions, 5000);
    return () => clearInterval(interval);
  }, [refreshSessions]);

  useEffect(() => {
    if (activeSession) {
      fetchSessionContext(activeSession.id);
    } else {
      setSessionContext(null);
    }
  }, [activeSession, fetchSessionContext]);

  const setActiveSession = useCallback((session: ShellSession | null) => {
    setActiveSessionRaw(session);
    persistActiveSessionId(session?.id || null);
    if (session) {
      outputRef.current = [];
      setOutput([]);
    }
  }, [persistActiveSessionId]);

  return {
    sessions,
    activeSession,
    sessionContext,
    output,
    isLoading,
    error,
    createSession,
    executeCommand,
    terminateSession,
    setActiveSession,
    refreshSessions,
    getAuditLog,
  };
}

export function getSessionStatusColor(status: SessionStatus): string {
  switch (status) {
    case "active":
      return "var(--success)";
    case "idle":
      return "var(--warning)";
    case "disconnected":
      return "var(--text-tertiary)";
    case "error":
      return "var(--danger)";
    default:
      return "var(--text-tertiary)";
  }
}

export function formatIdleTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

export function formatSessionTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
