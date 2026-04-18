"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useChat } from "@/hooks/useChat";
import { useProviders } from "@/hooks/useProviders";
import { buildThreadLocationLabel } from "@/lib/thread-store";
import { buildRuntimeStrip } from "@/lib/console-simplify";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { ChatProfileSelector } from "./ChatProfileSelector";
import { ThreadSidebar } from "./ThreadSidebar";
import { ModelInfo, ProviderInfo } from "@/types/providers";
import { TaskType } from "@/types/providers";
import { useWorkspacePersonalization } from "@/hooks/useWorkspacePersonalization";
import { WorkspacePreset } from "@/lib/workspace-personalization";

function ThreadIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export function ChatContainer() {
  const {
    preset,
    personalization,
    notice,
    dismissNotice,
    setPreset,
    setChatVisibility,
  } = useWorkspacePersonalization();
  const [isSidebarOpen, setIsSidebarOpen] = useState(personalization.chat.sidebarOpen);
  const [showRuntimeDetails, setShowRuntimeDetails] = useState(personalization.chat.showRuntimeDetails);
  const [showDiagnostics, setShowDiagnostics] = useState(personalization.chat.showDiagnostics);
  const [showAdvanced, setShowAdvanced] = useState(personalization.chat.showAdvanced);
  const {
    providers,
    models,
    isLoading: providersLoading,
    getModelsForProvider,
  } = useProviders();

  const {
    messages,
    isStreaming,
    streamingContent,
    attachedFiles,
    error,
    sendMessage,
    stopGeneration,
    addAttachment,
    removeAttachment,
    messagesEndRef,
    threads,
    pinnedThreads,
    recentThreads,
    groupedThreadsByProject,
    archivedThreads,
    activeThreadId,
    createThread,
    loadThread,
    deleteThread,
    togglePinThread,
    renameThread,
    moveThreadToProject,
    archiveThread,
    unarchiveThread,
    currentMode,
    setCurrentMode,
    currentProvider,
    setCurrentProvider,
    currentModel,
    setCurrentModel,
    currentProjectId,
    projects,
    workspaceSession,
    runtimeBinding,
    runtimeHealth,
    availableTools,
    runtimeDegradedStates,
    operatorActionSurface,
    runOperatorAction,
    isBulkSelectMode,
    selectedThreadIds,
    toggleBulkSelectMode,
    toggleThreadSelection,
    clearThreadSelection,
    mergeThreads,
    moveSelectedThreadsToProject,
    archiveSelectedThreads,
  } = useChat({ providers, models });

  const hasMessages = messages.length > 0;
  const activeThread = threads.find((thread) => thread.id === activeThreadId) || null;

  const diagnosticsAllowed = preset === "expert";
  const advancedAllowed = preset !== "guided";

  useEffect(() => {
    setIsSidebarOpen(personalization.chat.sidebarOpen);
    setShowRuntimeDetails(personalization.chat.showRuntimeDetails);
    setShowDiagnostics(personalization.chat.showDiagnostics);
    setShowAdvanced(personalization.chat.showAdvanced);
  }, [personalization.chat]);

  useEffect(() => {
    if (!diagnosticsAllowed && showDiagnostics) {
      setShowDiagnostics(false);
      setChatVisibility({ showDiagnostics: false });
    }
    if (!advancedAllowed && showAdvanced) {
      setShowAdvanced(false);
      setChatVisibility({ showAdvanced: false });
    }
  }, [advancedAllowed, diagnosticsAllowed, setChatVisibility, showAdvanced, showDiagnostics]);

  const projectNameById = useMemo(
    () => new Map(projects.map((project) => [project.project_id, project.name || project.project_id])),
    [projects]
  );

  const fallbackLocationLabel =
    currentProjectId && projectNameById.has(currentProjectId)
      ? `${projectNameById.get(currentProjectId)} / Workspace`
      : "No active thread";

  const currentLocationLabel = activeThread
    ? buildThreadLocationLabel(activeThread, projects)
    : fallbackLocationLabel;

  const runtimeStrip = buildRuntimeStrip({
    workspaceSession,
    runtimeBinding,
    currentLocationLabel,
    runtimeHealth,
    availableTools,
    degradedStates: runtimeDegradedStates,
    hasActiveThread: Boolean(activeThreadId),
  });

  const activeThreadTitle = activeThread?.title || "No active thread";
  const currentProjectLabel =
    (workspaceSession.project_id &&
      (projectNameById.get(workspaceSession.project_id) || workspaceSession.project_id)) ||
    "Unassigned";

  const handleCreateThread = (options?: {
    title?: string;
    projectId?: string;
    folderPath?: string;
    inheritProjectContext?: boolean;
  }) => {
    createThread({ inheritProjectContext: true, ...(options || {}) });
  };

  const handleSelectThread = (threadId: string) => {
    loadThread(threadId);
    if (window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

  const statusToneColor =
    runtimeStrip.statusTone === "success"
      ? "var(--success)"
      : runtimeStrip.statusTone === "danger"
        ? "var(--danger)"
        : "var(--warning)";

  return (
    <div className="h-full flex" style={{ background: "var(--base-00)" }}>
      {isSidebarOpen && (
        <ThreadSidebar
          threads={threads}
          pinnedThreads={pinnedThreads}
          recentThreads={recentThreads}
          groupedThreadsByProject={groupedThreadsByProject}
          archivedThreads={archivedThreads}
          projects={projects}
          activeThreadId={activeThreadId}
          onSelectThread={handleSelectThread}
          onCreateThread={handleCreateThread}
          onDeleteThread={deleteThread}
          onTogglePin={togglePinThread}
          onRenameThread={renameThread}
          onMoveThread={moveThreadToProject}
          onArchiveThread={archiveThread}
          onUnarchiveThread={unarchiveThread}
          onClose={() => setIsSidebarOpen(false)}
          isBulkSelectMode={isBulkSelectMode}
          selectedThreadIds={selectedThreadIds}
          onToggleBulkSelectMode={toggleBulkSelectMode}
          onToggleThreadSelection={toggleThreadSelection}
          onClearThreadSelection={clearThreadSelection}
          onMergeThreads={mergeThreads}
          onMoveSelectedThreadsToProject={moveSelectedThreadsToProject}
          onArchiveSelectedThreads={archiveSelectedThreads}
        />
      )}

      <div className="flex-1 min-w-0 flex flex-col h-full">
        {notice && (
          <div
            className="mx-4 lg:mx-6 mt-3 mb-0 rounded-lg px-3 py-2 flex items-start justify-between gap-3"
            style={{
              background: notice.tone === "warning" ? "rgba(245, 158, 11, 0.12)" : "rgba(14, 165, 233, 0.12)",
              border: `1px solid ${notice.tone === "warning" ? "rgba(245, 158, 11, 0.35)" : "rgba(14, 165, 233, 0.35)"}`,
              color: notice.tone === "warning" ? "var(--warning)" : "var(--live-cyan)",
            }}
          >
            <p className="text-sm">{notice.message}</p>
            <button
              onClick={dismissNotice}
              className="rounded px-2 py-1 text-xs"
              style={{ border: "1px solid var(--base-04)", color: "var(--text-secondary)", background: "var(--base-01)" }}
            >
              Dismiss
            </button>
          </div>
        )}

        <div
          className="px-4 lg:px-6 py-3 border-b"
          style={{ borderColor: "var(--base-04)", background: "var(--base-01)" }}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2 min-w-0">
              <button
                onClick={() => {
                  const next = !isSidebarOpen;
                  setIsSidebarOpen(next);
                  setChatVisibility({ sidebarOpen: next });
                }}
                className="p-2 rounded-lg transition-colors hover:bg-base-03"
                style={{ color: "var(--text-secondary)" }}
                title="Toggle thread rail"
              >
                <ThreadIcon />
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                  <h2 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                    {activeThreadTitle}
                  </h2>
                  <span
                    className="text-[11px] px-2 py-0.5 rounded shrink-0"
                    style={{ background: "var(--base-03)", color: statusToneColor, border: "1px solid var(--base-04)" }}
                  >
                    {runtimeStrip.status}
                  </span>
                </div>
                <div className="text-xs truncate mt-1" style={{ color: "var(--text-tertiary)" }}>
                  Project: {currentProjectLabel} · {runtimeStrip.location}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <label className="sr-only" htmlFor="chat-workspace-preset-select">
                Workspace preset
              </label>
              <select
                id="chat-workspace-preset-select"
                value={preset}
                onChange={(event) => setPreset(event.target.value as WorkspacePreset)}
                className="px-2 py-1 rounded text-xs"
                style={{
                  background: "var(--base-03)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--base-04)",
                }}
                title="Workspace preset"
              >
                <option value="guided">Guided</option>
                <option value="standard">Standard</option>
                <option value="expert">Expert</option>
              </select>
              {diagnosticsAllowed && (
                <button
                  onClick={() => {
                    const next = !showDiagnostics;
                    setShowDiagnostics(next);
                    setChatVisibility({ showDiagnostics: next });
                  }}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: showDiagnostics ? "var(--base-04)" : "var(--base-03)",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--base-04)",
                  }}
                >
                  {showDiagnostics ? "Hide diagnostics" : "Diagnostics"}
                </button>
              )}
              {advancedAllowed && (
                <button
                  onClick={() => {
                    const next = !showAdvanced;
                    setShowAdvanced(next);
                    setChatVisibility({ showAdvanced: next });
                  }}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: showAdvanced ? "var(--base-04)" : "var(--base-03)",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--base-04)",
                  }}
                >
                  {showAdvanced ? "Hide controls" : "Advanced"}
                </button>
              )}
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ChatProfileSelector
              mode={currentMode}
              onModeChange={setCurrentMode}
              provider={currentProvider}
              onProviderChange={setCurrentProvider}
              model={currentModel}
              onModelChange={setCurrentModel}
              providers={providers}
              models={getModelsForProvider(currentProvider)}
              isLoading={providersLoading}
            />
            <span
              className="text-[11px] px-2 py-1 rounded"
              style={{
                color: "var(--text-tertiary)",
                border: "1px solid var(--base-04)",
                background: "var(--base-02)",
              }}
            >
              Preset {preset}: {preset === "guided" ? "minimal controls" : preset === "standard" ? "balanced controls" : "diagnostics enabled"}
            </span>
          </div>
        </div>

        <div
          className="px-4 lg:px-6 py-2 border-b"
          style={{ borderColor: "var(--base-04)", background: "var(--base-00)" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="truncate" style={{ color: "var(--text-secondary)" }}>
              Runtime: {runtimeStrip.summary}
            </span>
            <div className="flex items-center gap-2 shrink-0">
              {runtimeStrip.degraded.length > 0 && (
                <span
                  className="px-2 py-0.5 rounded"
                  style={{ background: "rgba(245, 158, 11, 0.1)", color: "var(--warning)" }}
                >
                  Degraded: {runtimeStrip.degraded.length}
                </span>
              )}
              <button
                onClick={() => {
                  const next = !showRuntimeDetails;
                  setShowRuntimeDetails(next);
                  setChatVisibility({ showRuntimeDetails: next });
                }}
                className="px-2 py-0.5 rounded"
                style={{
                  background: "var(--base-03)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--base-04)",
                }}
              >
                {showRuntimeDetails ? "Hide runtime" : "Show runtime"}
              </button>
            </div>
          </div>

          {showRuntimeDetails && (
            <div className="mt-2 grid gap-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              <div>Location: {runtimeStrip.location}</div>
              <div className="flex flex-wrap gap-2">
                {runtimeStrip.details.map((detail) => (
                  <span key={detail}>{detail}</span>
                ))}
              </div>
              {runtimeStrip.degraded.length > 0 && (
                <div
                  className="rounded px-2 py-1"
                  style={{ background: "rgba(245, 158, 11, 0.1)", color: "var(--warning)" }}
                >
                  {runtimeStrip.degraded.join(" | ")}
                </div>
              )}
            </div>
          )}
        </div>

        {advancedAllowed && showAdvanced && (
          <div
            className="px-4 lg:px-6 py-2 border-b"
            style={{ borderColor: "var(--base-04)", background: "var(--base-01)" }}
          >
            <div className="flex flex-wrap gap-2 items-center">
              {operatorActionSurface.map((action) => (
                <button
                  key={action.id}
                  onClick={() => runOperatorAction(action.command)}
                  disabled={!action.enabled}
                  className="px-2 py-1 rounded text-xs transition-colors disabled:opacity-50"
                  style={{
                    background: "var(--base-03)",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--base-04)",
                  }}
                  title={`Run ${action.command}`}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {diagnosticsAllowed && showDiagnostics && (
          <div
            className="px-4 lg:px-6 py-3 border-b"
            style={{ borderColor: "var(--base-04)", background: "var(--base-01)" }}
          >
            <div className="text-xs font-medium mb-2" style={{ color: "var(--text-secondary)" }}>
              Runtime diagnostics
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
              <DiagnosticItem
                label="MCP Bridge"
                value={runtimeHealth.mcpHealthy ? "Connected" : "Disconnected"}
                tone={runtimeHealth.mcpHealthy ? "success" : "danger"}
              />
              <DiagnosticItem
                label="LLM Proxy"
                value={runtimeHealth.llmHealthy ? "Connected" : "Disconnected"}
                tone={runtimeHealth.llmHealthy ? "success" : "danger"}
              />
              <DiagnosticItem label="Tools" value={String(availableTools.length)} tone="neutral" />
              <DiagnosticItem label="Projects" value={String(projects.length)} tone="neutral" />
              <DiagnosticItem
                label="Thread ID"
                value={activeThreadId ? activeThreadId.slice(0, 8) : "none"}
                tone="neutral"
                mono
              />
              <DiagnosticItem
                label="Session"
                value={runtimeBinding.status}
                tone={
                  runtimeBinding.status === "bound"
                    ? "success"
                    : runtimeBinding.status === "invalid"
                      ? "danger"
                      : "warning"
                }
              />
            </div>
            {runtimeBinding.error && (
              <div
                className="mt-2 rounded px-2 py-1 text-xs"
                style={{ background: "rgba(239, 68, 68, 0.1)", color: "var(--danger)" }}
              >
                Error: {runtimeBinding.error}
              </div>
            )}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-4 py-6 lg:px-6">
          {!hasMessages ? (
            <WelcomeScreen
              onSuggestion={sendMessage}
              providers={providers}
              models={models}
              currentMode={currentMode}
              setCurrentMode={setCurrentMode}
              currentProvider={currentProvider}
              setCurrentProvider={setCurrentProvider}
              currentModel={currentModel}
              setCurrentModel={setCurrentModel}
              getModelsForProvider={getModelsForProvider}
              providersLoading={providersLoading}
            />
          ) : (
            <div className="max-w-3xl mx-auto space-y-3">
              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isStreaming={isStreaming && message.role === "assistant" && index === messages.length - 1}
                />
              ))}

              {isStreaming && streamingContent && (
                <div className="flex justify-start mb-4 motion-safe:animate-pulse">
                  <div
                    className="max-w-[90%] rounded-xl px-4 py-3 border"
                    style={{ borderColor: "var(--base-04)", color: "var(--text-primary)", background: "var(--base-01)" }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center"
                        style={{ background: "var(--accent-primary)" }}
                      >
                        <BotIcon />
                      </div>
                      <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                        Assistant
                      </span>
                      <span className="flex items-center gap-1 text-xs" style={{ color: "var(--live-cyan)" }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-live" />
                        Thinking...
                      </span>
                    </div>
                    <div className="text-sm whitespace-pre-wrap">
                      {streamingContent}
                      <span className="animate-pulse">▊</span>
                    </div>
                  </div>
                </div>
              )}

              {error && !isStreaming && (
                <div
                  className="max-w-3xl mx-auto mt-4 p-4 rounded-lg border"
                  style={{ background: "rgba(239, 68, 68, 0.1)", borderColor: "var(--danger)", color: "var(--danger)" }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <ErrorIcon />
                    <span className="font-medium">Error</span>
                  </div>
                  <p className="text-sm">{error}</p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t px-4 py-4 lg:px-6" style={{ borderColor: "var(--base-04)", background: "var(--base-01)" }}>
          <div className="max-w-3xl mx-auto">
            <ChatInput
              onSend={sendMessage}
              onFileSelect={addAttachment}
              attachedFiles={attachedFiles}
              onRemoveFile={removeAttachment}
              isStreaming={isStreaming}
              onStop={stopGeneration}
              placeholder="Message the control plane..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function DiagnosticItem({
  label,
  value,
  tone,
  mono = false,
}: {
  label: string;
  value: string;
  tone: "success" | "warning" | "danger" | "neutral";
  mono?: boolean;
}) {
  const color =
    tone === "success"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "danger"
          ? "var(--danger)"
          : "var(--text-primary)";

  return (
    <div className="rounded px-2 py-1.5" style={{ background: "var(--base-02)", border: "1px solid var(--base-04)" }}>
      <div className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
        {label}
      </div>
      <div className={`text-xs ${mono ? "font-mono" : ""}`} style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function WelcomeScreen({
  onSuggestion,
  providers,
  models,
  currentMode,
  setCurrentMode,
  currentProvider,
  setCurrentProvider,
  currentModel,
  setCurrentModel,
  getModelsForProvider,
  providersLoading,
}: {
  onSuggestion: (text: string) => void;
  providers: ProviderInfo[];
  models: ModelInfo[];
  currentMode: TaskType;
  setCurrentMode: (mode: TaskType) => void;
  currentProvider: string;
  setCurrentProvider: (providerId: string) => void;
  currentModel: string;
  setCurrentModel: (modelId: string) => void;
  getModelsForProvider: (providerId: string) => ModelInfo[];
  providersLoading: boolean;
}) {
  const suggestions = [
    {
      icon: <SecurityIcon />,
      title: "Run security audit",
      description: "Check system security status",
      prompt: "Run a security audit on my system",
    },
    {
      icon: <SystemIcon />,
      title: "System health check",
      description: "View CPU, GPU, and memory stats",
      prompt: "Check my system health",
    },
    {
      icon: <CodeIcon />,
      title: "Analyze code",
      description: "Get insights on your codebase",
      prompt: "Analyze the codebase in /home/lch/projects/bazzite-laptop",
    },
    {
      icon: <HelpIcon />,
      title: "What can you do?",
      description: "Learn about available commands",
      prompt: "What can you help me with?",
    },
  ];

  return (
    <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center px-4">
      <div
        className="w-14 h-14 rounded-xl flex items-center justify-center mb-5 motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in motion-safe:duration-300"
        style={{ background: "var(--base-02)" }}
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: "var(--accent-primary)" }}>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2
        className="text-2xl font-semibold mb-2 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-100"
        style={{ color: "var(--text-primary)" }}
      >
        Chat Workspace
      </h2>
      <p
        className="mb-4 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-150"
        style={{ color: "var(--text-secondary)" }}
      >
        Thread-aware, project-bound, and runtime-truthful.
      </p>
      <div className="w-full flex justify-center mb-6 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-200">
        <ChatProfileSelector
          mode={currentMode}
          onModeChange={setCurrentMode}
          provider={currentProvider}
          onProviderChange={setCurrentProvider}
          model={currentModel}
          onModelChange={setCurrentModel}
          providers={providers}
          models={getModelsForProvider(currentProvider)}
          isLoading={providersLoading}
        />
      </div>
      <p
        className="mb-8 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-250"
        style={{ color: "var(--text-secondary)" }}
      >
        Start with a prompt or one of these actions.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.title}
            onClick={() => onSuggestion(suggestion.prompt)}
            className="flex items-start gap-3 p-4 rounded-xl border text-left transition-all hover:border-[var(--accent-primary)] motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300"
            style={{
              background: "var(--base-02)",
              borderColor: "var(--base-04)",
              animationDelay: `${200 + index * 50}ms`,
            }}
          >
            <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--base-03)" }}>
              {suggestion.icon}
            </div>
            <div>
              <div className="font-medium mb-0.5" style={{ color: "var(--text-primary)" }}>
                {suggestion.title}
              </div>
              <div className="text-sm" style={{ color: "var(--text-tertiary)" }}>
                {suggestion.description}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function BotIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "white" }}>
      <rect width="18" height="10" x="3" y="11" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function SecurityIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--success)" }}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function SystemIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--accent-primary)" }}>
      <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="9" y1="21" x2="9" y2="9" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--accent-secondary)" }}>
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--warning)" }}>
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}
