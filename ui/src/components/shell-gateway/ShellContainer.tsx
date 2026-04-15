"use client";

import { useState, useCallback } from "react";
import { useShellSessions } from "@/hooks/useShellSessions";
import { ShellSession } from "@/types/shell";
import { SessionTabs } from "./SessionTabs";
import { TerminalCanvas } from "./TerminalCanvas";
import { ShellAuditStrip } from "./ShellAuditStrip";
import { ShellStatusBar } from "./ShellStatusBar";
import { ShellSidePane } from "./ShellSidePane";

export function ShellContainer() {
  const {
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
  } = useShellSessions();

  const [showSidePane, setShowSidePane] = useState(false);
  const [sidePaneTab, setSidePaneTab] = useState<"logs" | "artifacts">("logs");
  const [commandInput, setCommandInput] = useState("");

  const handleCreateSession = useCallback(async () => {
    try {
      const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      await createSession(`Session ${timestamp}`);
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  }, [createSession]);

  const handleExecuteCommand = useCallback(async () => {
    if (!activeSession || !commandInput.trim()) return;
    
    const command = commandInput.trim();
    setCommandInput("");
    
    try {
      await executeCommand(activeSession.id, command);
    } catch (err) {
      console.error("Command failed:", err);
    }
  }, [activeSession, commandInput, executeCommand]);

  const handleTerminateSession = useCallback(async (sessionId: string) => {
    try {
      await terminateSession(sessionId);
    } catch (err) {
      console.error("Failed to terminate session:", err);
    }
  }, [terminateSession]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleExecuteCommand();
    }
  }, [handleExecuteCommand]);

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--base-00)" }}>
      {/* Shell Header */}
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
            Interactive Shell
          </h2>
          <ShellStatusBar
            session={activeSession}
            context={sessionContext}
            isLoading={isLoading}
            error={error}
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSidePane(!showSidePane)}
            className="px-3 py-1.5 text-xs rounded-md transition-colors"
            style={{
              background: showSidePane ? "var(--base-03)" : "var(--base-02)",
              color: "var(--text-secondary)",
              border: "1px solid var(--base-04)",
            }}
          >
            {showSidePane ? "Hide Sidebar" : "Show Sidebar"}
          </button>
          <button
            onClick={handleCreateSession}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs rounded-md transition-colors disabled:opacity-50"
            style={{
              background: "var(--accent-primary)",
              color: "white",
            }}
          >
            + New Session
          </button>
        </div>
      </div>

      {/* Session Tabs */}
      <SessionTabs
        sessions={sessions}
        activeSession={activeSession}
        onSelectSession={setActiveSession}
        onCreateSession={handleCreateSession}
        onTerminateSession={handleTerminateSession}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Terminal Canvas */}
        <div className="flex-1 flex flex-col min-w-0">
          <TerminalCanvas
            output={output}
            session={activeSession}
            isLoading={isLoading}
          />

          {/* Command Input */}
          {activeSession && activeSession.status === "active" && (
            <div
              className="px-4 py-3 border-t"
              style={{
                background: "var(--base-01)",
                borderColor: "var(--base-04)",
              }}
            >
              <div className="flex items-center gap-3">
                <span
                  className="text-sm font-mono"
                  style={{ color: "var(--accent-primary)" }}
                >
                  $
                </span>
                <input
                  type="text"
                  value={commandInput}
                  onChange={(e) => setCommandInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Enter command..."
                  className="flex-1 bg-transparent text-sm font-mono outline-none"
                  style={{ color: "var(--text-primary)" }}
                  autoFocus
                />
                <button
                  onClick={handleExecuteCommand}
                  disabled={!commandInput.trim() || isLoading}
                  className="px-3 py-1 text-xs rounded transition-colors disabled:opacity-50"
                  style={{
                    background: commandInput.trim() ? "var(--accent-primary)" : "var(--base-03)",
                    color: "white",
                  }}
                >
                  Run
                </button>
              </div>
            </div>
          )}
          {activeSession && activeSession.status !== "active" && activeSession.status !== "idle" && (
            <div
              className="px-4 py-2 border-t text-xs"
              style={{
                background: "var(--base-01)",
                borderColor: "var(--base-04)",
                color: "var(--text-tertiary)",
              }}
            >
              {activeSession.status === "disconnected"
                ? "Session disconnected — terminate and create a new session to continue"
                : activeSession.status === "error"
                ? `Session error — terminate and create a new session`
                : `Session ${activeSession.status} — no commands accepted`}
            </div>
          )}

          {/* Audit Strip */}
          <ShellAuditStrip
            session={activeSession}
            context={sessionContext}
          />
        </div>

        {/* Side Pane */}
        {showSidePane && (
          <ShellSidePane
            activeTab={sidePaneTab}
            onTabChange={setSidePaneTab}
            session={activeSession}
          />
        )}
      </div>
    </div>
  );
}
