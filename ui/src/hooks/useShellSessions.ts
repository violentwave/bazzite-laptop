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

export function useShellSessions(): UseShellSessionsReturn {
  const [sessions, setSessions] = useState<ShellSession[]>([]);
  const [activeSession, setActiveSession] = useState<ShellSession | null>(null);
  const [sessionContext, setSessionContext] = useState<SessionContext | null>(null);
  const [output, setOutput] = useState<TerminalOutput[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const outputRef = useRef<TerminalOutput[]>([]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await callMCPTool("shell.list_sessions");
      if (Array.isArray(data)) {
        const sessionList = data as ShellSession[];
        setSessions(sessionList);
        // Update active session if it exists in the list
        if (activeSession) {
          const updated = sessionList.find((s) => s.id === activeSession.id);
          if (updated) {
            setActiveSession(updated);
          }
        }
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? `Shell session refresh failed: ${err.message}`
          : "Shell session refresh failed"
      );
    }
  }, [activeSession]);

  const fetchSessionContext = useCallback(async (sessionId: string) => {
    try {
      const data = await callMCPTool("shell.get_context", { session_id: sessionId });
      if (data && typeof data === "object" && !("error" in data)) {
        setSessionContext(data as SessionContext);
      }
    } catch (err) {
      console.error("Failed to fetch session context:", err);
    }
  }, []);

  const createSession = useCallback(async (name?: string, cwd?: string): Promise<ShellSession> => {
    setIsLoading(true);
    setError(null);
    try {
      const session = (await callMCPTool("shell.create_session", {
        name,
        cwd,
      })) as ShellSession;
      await refreshSessions();
      setActiveSession(session);
      
      // Add system message
      const systemOutput: TerminalOutput = {
        type: "system",
        content: `Session created: ${session.name} (${session.id})`,
        timestamp: new Date().toISOString(),
      };
      outputRef.current = [systemOutput];
      setOutput(outputRef.current);
      
      return session;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refreshSessions]);

  const executeCommand = useCallback(async (sessionId: string, command: string): Promise<CommandResult> => {
    // Add command to output
    const commandOutput: TerminalOutput = {
      type: "input",
      content: `$ ${command}`,
      timestamp: new Date().toISOString(),
    };
    outputRef.current = [...outputRef.current, commandOutput];
    setOutput(outputRef.current);

    try {
      const result = await callMCPTool("shell.execute_command", {
        session_id: sessionId,
        command,
      }) as CommandResult;

      // Add output
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
      setOutput(outputRef.current);

      // Refresh session context
      await fetchSessionContext(sessionId);

      return result;
    } catch (err) {
      const errorOutput: TerminalOutput = {
        type: "error",
        content: err instanceof Error ? err.message : "Command failed",
        timestamp: new Date().toISOString(),
      };
      outputRef.current = [...outputRef.current, errorOutput];
      setOutput(outputRef.current);
      
      return { success: false, error: err instanceof Error ? err.message : "Command failed" };
    }
  }, [fetchSessionContext]);

  const terminateSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      await callMCPTool("shell.terminate_session", { session_id: sessionId });
      await refreshSessions();
      
      if (activeSession?.id === sessionId) {
        setActiveSession(null);
        setSessionContext(null);
        outputRef.current = [];
        setOutput([]);
      }
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to terminate session");
      return false;
    }
  }, [activeSession, refreshSessions]);

  const getAuditLog = useCallback(async (sessionId?: string, limit?: number): Promise<AuditLogEntry[]> => {
    try {
      const data = await callMCPTool("shell.get_audit_log", { session_id: sessionId, limit });
      return Array.isArray(data) ? data : [];
    } catch (err) {
      console.error("Failed to fetch audit log:", err);
      return [];
    }
  }, []);

  // Load sessions on mount and refresh periodically
  useEffect(() => {
    refreshSessions();
    const interval = setInterval(refreshSessions, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [refreshSessions]);

  // Fetch context when active session changes
  useEffect(() => {
    if (activeSession) {
      fetchSessionContext(activeSession.id);
    } else {
      setSessionContext(null);
    }
  }, [activeSession, fetchSessionContext]);

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

/** Get status color for UI */
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

/** Format idle time for display */
export function formatIdleTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

/** Format timestamp for display */
export function formatSessionTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
