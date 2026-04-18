"use client";

import React, { useState } from 'react';
import { useChat } from '@/hooks/useChat';
import { useProviders } from '@/hooks/useProviders';
import { buildThreadLocationLabel } from '@/lib/thread-store';
import { buildRuntimeStrip } from '@/lib/console-simplify';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ChatProfileSelector } from './ChatProfileSelector';
import { ThreadSidebar } from './ThreadSidebar';
import { ModelInfo, ProviderInfo } from '@/types/providers';
import { TaskType } from '@/types/providers';

function ThreadIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export function ChatContainer() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showRuntimeDetails, setShowRuntimeDetails] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
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
  const currentLocationLabel = activeThread
    ? buildThreadLocationLabel(activeThread, projects)
    : 'No active thread';
  const runtimeStrip = buildRuntimeStrip({
    workspaceSession,
    runtimeBinding,
    currentLocationLabel,
    runtimeHealth,
    availableTools,
    degradedStates: runtimeDegradedStates,
    hasActiveThread: Boolean(activeThreadId),
  });

  const handleCreateThread = (options?: { title?: string; projectId?: string; folderPath?: string; inheritProjectContext?: boolean }) => {
    createThread({ inheritProjectContext: true, ...(options || {}) });
    setIsSidebarOpen(false);
  };

  const handleSelectThread = (threadId: string) => {
    loadThread(threadId);
    setIsSidebarOpen(false);
  };

  return (
    <div className="h-full flex">
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
      <div className="flex-1 flex flex-col h-full">
        <div className="flex items-center justify-between px-4 py-2 border-b shrink-0" style={{ borderColor: 'var(--base-04)', background: 'var(--base-02)' }}>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded-lg transition-colors hover:bg-base-03"
              style={{ color: 'var(--text-secondary)' }}
              title="Toggle threads"
            >
              <ThreadIcon />
            </button>
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
          <div className="flex items-center gap-2">
            {hasMessages && (
              <>
                <button
                  onClick={() => setShowDiagnostics((prev) => !prev)}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: 'var(--base-03)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--base-04)',
                  }}
                >
                  {showDiagnostics ? 'Hide diagnostics' : 'Diagnostics'}
                </button>
                <button
                  onClick={() => setShowRuntimeDetails((prev) => !prev)}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: 'var(--base-03)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--base-04)',
                  }}
                >
                  {showRuntimeDetails ? 'Hide details' : 'Show details'}
                </button>
              </>
            )}
            <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Local threads, organized in sidebar
            </div>
          </div>
        </div>
        {hasMessages && (
          <div
            className="px-4 py-2 border-b text-xs flex items-center justify-between gap-2"
            style={{ borderColor: 'var(--base-04)', background: 'var(--base-01)' }}
          >
            <span className="truncate" style={{ color: 'var(--text-secondary)' }}>
              Runtime: {runtimeStrip.summary}
            </span>
            <span
              className="font-medium shrink-0"
              style={{
                color:
                  runtimeStrip.statusTone === 'success'
                    ? 'var(--success)'
                    : runtimeStrip.statusTone === 'danger'
                      ? 'var(--danger)'
                      : 'var(--warning)',
              }}
            >
              {runtimeStrip.status}
            </span>
          </div>
        )}
        {hasMessages && (
          <div
            className="px-4 py-2 border-b"
            style={{ borderColor: 'var(--base-04)', background: 'var(--base-01)' }}
          >
            <div className="flex flex-wrap gap-2 items-center">
              {operatorActionSurface.map((action) => (
                <button
                  key={action.id}
                  onClick={() => runOperatorAction(action.command)}
                  disabled={!action.enabled}
                  className="px-2 py-1 rounded text-xs transition-colors disabled:opacity-50"
                  style={{
                    background: 'var(--base-03)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--base-04)',
                  }}
                  title={`Run ${action.command}`}
                >
                  {action.label}
                </button>
              ))}
              {runtimeStrip.degraded.length > 0 && (
                <span
                  className="text-[11px] rounded px-2 py-1"
                  style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--warning)' }}
                >
                  Degraded: {runtimeStrip.degraded.length}
                </span>
              )}
            </div>
            {showRuntimeDetails && (
              <div className="mt-2 space-y-1 text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
                <div>Location: {runtimeStrip.location}</div>
                <div className="flex flex-wrap gap-3">
                  {runtimeStrip.details.map((detail) => (
                    <span key={detail}>{detail}</span>
                  ))}
                </div>
                {runtimeStrip.degraded.length > 0 && (
                  <div
                    className="rounded px-2 py-1"
                    style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--warning)' }}
                  >
                    {runtimeStrip.degraded.join(' | ')}
                  </div>
                )}
              </div>
            )}
            {showDiagnostics && (
              <div className="mt-2 space-y-2 text-[11px]" style={{ color: 'var(--text-tertiary)', borderTop: '1px solid var(--base-04)', paddingTop: '8px' }}>
                <div className="font-medium" style={{ color: 'var(--text-secondary)' }}>Diagnostics</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span style={{ color: 'var(--text-tertiary)' }}>MCP Bridge:</span>{' '}
                    <span style={{ color: runtimeHealth.mcpHealthy ? 'var(--success)' : 'var(--danger)' }}>
                      {runtimeHealth.mcpHealthy ? 'connected' : 'disconnected'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-tertiary)' }}>LLM Proxy:</span>{' '}
                    <span style={{ color: runtimeHealth.llmHealthy ? 'var(--success)' : 'var(--danger)' }}>
                      {runtimeHealth.llmHealthy ? 'connected' : 'disconnected'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-tertiary)' }}>Tools available:</span>{' '}
                    <span>{availableTools.length}</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-tertiary)' }}>Projects registered:</span>{' '}
                    <span>{projects.length}</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-tertiary)' }}>Thread ID:</span>{' '}
                    <span className="font-mono">{activeThreadId?.slice(0, 8) || 'none'}</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-tertiary)' }}>Session bound:</span>{' '}
                    <span style={{ 
                      color: runtimeBinding.status === 'bound' ? 'var(--success)' : 
                             runtimeBinding.status === 'invalid' ? 'var(--danger)' : 'var(--warning)' 
                    }}>
                      {runtimeBinding.status}
                    </span>
                  </div>
                </div>
                {runtimeBinding.error && (
                  <div className="rounded px-2 py-1" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)' }}>
                    Error: {runtimeBinding.error}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
           <div className="flex-1 overflow-y-auto px-4 py-6">
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
              <div className="max-w-3xl mx-auto space-y-2">
              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isStreaming={isStreaming && message.role === 'assistant' && index === messages.length - 1}
                />
              ))}
              {isStreaming && streamingContent && (
                <div className="flex justify-start mb-4 motion-safe:animate-pulse">
                  <div className="max-w-[90%] rounded-lg pl-4 py-2" style={{ borderLeft: '3px solid var(--accent-primary)', color: 'var(--text-primary)' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ background: 'var(--accent-primary)' }}>
                        <BotIcon />
                      </div>
                      <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Assistant</span>
                      <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--live-cyan)' }}>
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
                <div className="max-w-3xl mx-auto mt-4 p-4 rounded-lg border-l-[3px]" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'var(--danger)', color: 'var(--danger)' }}>
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
        <div className="border-t px-4 py-4" style={{ borderColor: 'var(--base-04)' }}>
          <div className="max-w-3xl mx-auto">
            <ChatInput
              onSend={sendMessage}
              onFileSelect={addAttachment}
              attachedFiles={attachedFiles}
              onRemoveFile={removeAttachment}
              isStreaming={isStreaming}
              onStop={stopGeneration}
              placeholder="Ask anything or type / for commands..."
            />
          </div>
        </div>
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
    { icon: <SecurityIcon />, title: 'Run security audit', description: 'Check system security status', prompt: 'Run a security audit on my system' },
    { icon: <SystemIcon />, title: 'System health check', description: 'View CPU, GPU, and memory stats', prompt: 'Check my system health' },
    { icon: <CodeIcon />, title: 'Analyze code', description: 'Get insights on your codebase', prompt: 'Analyze the codebase in /home/lch/projects/bazzite-laptop' },
    { icon: <HelpIcon />, title: 'What can you do?', description: 'Learn about available commands', prompt: 'What can you help me with?' },
  ];

  return (
    <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center px-4">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in motion-safe:duration-300" style={{ background: 'var(--base-02)' }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--accent-primary)' }}>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2 className="text-2xl font-semibold mb-2 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-100" style={{ color: 'var(--text-primary)' }}>
        Welcome to Bazzite Control Console
      </h2>
      <p className="mb-4 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-150" style={{ color: 'var(--text-secondary)' }}>
        Your AI-powered operator console for Bazzite.
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
      <p className="mb-8 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:delay-250" style={{ color: 'var(--text-secondary)' }}>
        Ask me anything or try one of these suggestions.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.title}
            onClick={() => onSuggestion(suggestion.prompt)}
            className="flex items-start gap-3 p-4 rounded-xl border text-left transition-all hover:border-[var(--accent-primary)] motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300"
            style={{ background: 'var(--base-02)', borderColor: 'var(--base-04)', animationDelay: `${200 + index * 50}ms` }}
          >
            <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ background: 'var(--base-03)' }}>
              {suggestion.icon}
            </div>
            <div>
              <div className="font-medium mb-0.5" style={{ color: 'var(--text-primary)' }}>{suggestion.title}</div>
              <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{suggestion.description}</div>
            </div>
          </button>
        ))}
      </div>
      <div className="mt-8 flex items-center gap-4 text-sm motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300 motion-safe:delay-500" style={{ color: 'var(--text-tertiary)' }}>
        <span className="flex items-center gap-1">
          <kbd className="px-2 py-0.5 rounded text-xs" style={{ background: 'var(--base-03)', border: '1px solid var(--base-04)' }}>Ctrl+K</kbd>
          Command palette
        </span>
        <span className="flex items-center gap-1">
          <kbd className="px-2 py-0.5 rounded text-xs" style={{ background: 'var(--base-03)', border: '1px solid var(--base-04)' }}>Shift+Enter</kbd>
          New line
        </span>
      </div>
    </div>
  );
}

function BotIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'white' }}>
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
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--success)' }}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function SystemIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--accent-primary)' }}>
      <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="9" y1="21" x2="9" y2="9" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--accent-secondary)' }}>
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--warning)' }}>
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}
