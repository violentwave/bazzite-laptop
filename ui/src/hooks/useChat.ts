"use client";

import { useReducer, useCallback, useRef, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import {
  Message,
  Thread,
  Attachment,
  ContextPin,
  TokenUsage,
  ToolResult,
  ChatWorkspaceSession,
  RuntimeBindingMetadata,
  WorkspaceMode,
} from '@/types/chat';
import { ModelInfo, ProviderInfo } from '@/types/providers';
import { streamChatCompletion } from '@/lib/llm-client';
import { checkLLMProxyHealth } from '@/lib/llm-client';
import {
  checkMCPBridgeHealth,
  executeTool,
  formatToolResult,
  callMCPTool,
  listTools,
} from '@/lib/mcp-client';
import {
  buildRuntimeMetadata,
  modelsForProvider,
  validateWorkspaceSessionBinding,
} from '@/lib/workspace-session-binding';
import {
  buildDegradedStateSummary,
  buildRuntimeIntrospectionResponse,
  classifyToolFailure,
  detectOperatorIntent,
  getOperatorActionSurface,
  summarizeToolArguments,
} from '@/lib/operator-runtime';

import {
  groupThreads,
  mergeThreadsInStore,
  moveThreadToProjectInStore,
  normalizeThread,
  renameThreadInStore,
  setThreadArchivedState,
  updateThreadInStore,
} from '@/lib/thread-store';

const THREADS_STORAGE_KEY = 'bazzite-chat-threads';
const ACTIVE_THREAD_KEY = 'bazzite-active-thread';

interface ThreadStore {
  version: number;
  threads: Thread[];
  activeThreadId: string | null;
}

interface UseChatOptions {
  providers?: ProviderInfo[];
  models?: ModelInfo[];
}

interface WorkbenchProject {
  project_id: string;
  name?: string;
  root_path?: string;
}

interface RuntimeHealthState {
  mcpHealthy: boolean;
  llmHealthy: boolean;
  toolsAvailable: boolean;
}

const DEFAULT_MODE: WorkspaceMode = 'fast';

function createEmptyWorkspaceSession(threadId: string | null): ChatWorkspaceSession {
  return {
    thread_id: threadId || '',
    project_id: '',
    mode: DEFAULT_MODE,
    provider: '',
    model: '',
    memory_policy: 'project-bound',
    tool_policy: 'mcp-governed',
    attached_context_sources: ['thread-history'],
    bound_at: '',
  };
}

function loadThreadStore(): ThreadStore {
  if (typeof window === 'undefined') {
    return { version: 1, threads: [], activeThreadId: null };
  }
  try {
    const stored = localStorage.getItem(THREADS_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<ThreadStore>;
      const threads = Array.isArray(parsed.threads)
        ? parsed.threads.map((thread) => normalizeThread(thread))
        : [];
      return {
        version: 2,
        threads,
        activeThreadId: parsed.activeThreadId || null,
      };
    }
  } catch {
    // Ignore parse errors
  }
  return { version: 2, threads: [], activeThreadId: null };
}

function saveThreadStore(store: ThreadStore): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(THREADS_STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Ignore storage errors
  }
}

function serializeMessages(msgs: Message[]): Record<string, unknown>[] {
  return msgs.map(m => ({
    ...m,
    timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : m.timestamp,
    toolCalls: m.toolCalls?.map(tc => ({
      ...tc,
      timestamp: tc.timestamp instanceof Date ? tc.timestamp.toISOString() : tc.timestamp,
    })),
    attachments: m.attachments?.map(a => ({ ...a })),
  }));
}

interface SerializedMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  timestamp: string;
  toolCalls?: SerializedToolCall[];
  attachments?: Attachment[];
  isStreaming?: boolean;
  error?: string;
  runtimeMetadata?: RuntimeBindingMetadata;
}

interface SerializedToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  argumentsSummary?: string;
  result?: ToolResult;
  status: 'pending' | 'success' | 'error' | 'blocked';
  timestamp: string;
}

function deserializeMessages(msgs: unknown[]): Message[] {
  return (msgs as SerializedMessage[]).map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: new Date(m.timestamp),
    toolCalls: m.toolCalls?.map((tc) => ({
      id: tc.id,
      name: tc.name,
      arguments: tc.arguments,
      argumentsSummary: tc.argumentsSummary,
      result: tc.result,
      status: tc.status,
      timestamp: new Date(tc.timestamp),
    })),
    attachments: m.attachments,
    isStreaming: m.isStreaming,
    error: m.error,
    runtimeMetadata: m.runtimeMetadata,
  }));
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  attachedFiles: Attachment[];
  contextPins: ContextPin[];
  tokenUsage: TokenUsage;
  error: string | null;
}

type ChatAction =
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: { id: string; updates: Partial<Message> } }
  | { type: 'SET_STREAMING'; payload: boolean }
  | { type: 'SET_STREAMING_CONTENT'; payload: string }
  | { type: 'APPEND_STREAMING_CONTENT'; payload: string }
  | { type: 'CLEAR_STREAMING_CONTENT' }
  | { type: 'ADD_ATTACHMENT'; payload: Attachment }
  | { type: 'REMOVE_ATTACHMENT'; payload: string }
  | { type: 'ADD_CONTEXT_PIN'; payload: ContextPin }
  | { type: 'REMOVE_CONTEXT_PIN'; payload: string }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_MESSAGES' };

const initialState: ChatState = {
  messages: [],
  isStreaming: false,
  streamingContent: '',
  attachedFiles: [],
  contextPins: [],
  tokenUsage: { input: 0, output: 0, total: 0 },
  error: null,
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };
    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === action.payload.id ? { ...msg, ...action.payload.updates } : msg
        ),
      };
    case 'SET_STREAMING':
      return { ...state, isStreaming: action.payload };
    case 'SET_STREAMING_CONTENT':
      return { ...state, streamingContent: action.payload };
    case 'APPEND_STREAMING_CONTENT':
      return { ...state, streamingContent: state.streamingContent + action.payload };
    case 'CLEAR_STREAMING_CONTENT':
      return { ...state, streamingContent: '' };
    case 'ADD_ATTACHMENT':
      return {
        ...state,
        attachedFiles: [...state.attachedFiles, action.payload],
      };
    case 'REMOVE_ATTACHMENT':
      return {
        ...state,
        attachedFiles: state.attachedFiles.filter((f) => f.id !== action.payload),
      };
    case 'ADD_CONTEXT_PIN':
      return {
        ...state,
        contextPins: [...state.contextPins, action.payload],
      };
    case 'REMOVE_CONTEXT_PIN':
      return {
        ...state,
        contextPins: state.contextPins.filter((p) => p.id !== action.payload),
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'CLEAR_MESSAGES':
      return { ...state, messages: [] };
    default:
      return state;
  }
}

export function useChat(options: UseChatOptions = {}) {
  const { providers = [], models = [] } = options;
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const abortControllerRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingContentRef = useRef('');
  const assistantIdRef = useRef<string | null>(null);
  
  // Thread management state
  const [threadStore, setThreadStore] = useState<ThreadStore>(() => loadThreadStore());
  const [activeThreadId, setActiveThreadId] = useState<string | null>(threadStore.activeThreadId);
  const [selectedThreadIds, setSelectedThreadIds] = useState<string[]>([]); // New: for bulk selection
  const [isBulkSelectMode, setIsBulkSelectMode] = useState(false); // New: for bulk selection mode
  const [workspaceSession, setWorkspaceSession] = useState<ChatWorkspaceSession>(() =>
    createEmptyWorkspaceSession(threadStore.activeThreadId)
  );
  const [runtimeBinding, setRuntimeBinding] = useState<{
    status: 'pending' | 'bound' | 'invalid';
    error: string | null;
  }>({ status: 'pending', error: null });
  const [availableProjects, setAvailableProjects] = useState<WorkbenchProject[]>([]);
  const [availableTools, setAvailableTools] = useState<string[]>([]);
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealthState>({
    mcpHealthy: false,
    llmHealthy: false,
    toolsAvailable: false,
  });

  const currentProvider = workspaceSession.provider;
  const currentModel = workspaceSession.model;
  const currentProjectId = workspaceSession.project_id;

  const getRuntimeSystemPrompt = useCallback((session: ChatWorkspaceSession) => {
    const metadata = buildRuntimeMetadata(session);
    const project = metadata.project_id || 'none';
    const sources = metadata.attached_context_sources.join(', ') || 'none';
    const projectContextAvailable = !session.project_id
      ? true
      : availableProjects.some((item) => item.project_id === session.project_id);
    const degraded = buildDegradedStateSummary({
      mcpHealthy: runtimeHealth.mcpHealthy,
      runtimeBinding,
      projectContextAvailable,
      toolsAvailable: runtimeHealth.toolsAvailable,
    });

    return [
      'Bazzite operator runtime binding (truth source for this thread):',
      `provider=${metadata.provider}`,
      `model=${metadata.model}`,
      `mode=${metadata.mode}`,
      `project=${project}`,
      `memory_policy=${metadata.memory_policy}`,
      `tool_policy=${metadata.tool_policy}`,
      `mcp_status=${runtimeHealth.mcpHealthy ? 'healthy' : 'degraded'}`,
      `llm_status=${runtimeHealth.llmHealthy ? 'healthy' : 'degraded'}`,
      `tool_count=${availableTools.length}`,
      `context_sources=${sources}`,
      `degraded_states=${degraded.join(' | ') || 'none'}`,
      'When asked about runtime identity, report these values exactly.',
      'Never claim a different provider/model/mode/project than shown here.',
      'Never claim tool access if mcp_status is degraded or tool_count is 0.',
      'Never claim direct OS/screen access without mediated tool execution.',
    ].join('\n');
  }, [
    availableProjects,
    availableTools.length,
    runtimeBinding,
    runtimeHealth.llmHealthy,
    runtimeHealth.mcpHealthy,
    runtimeHealth.toolsAvailable,
  ]);

  const setSessionPatch = useCallback((patch: Partial<ChatWorkspaceSession>) => {
    setWorkspaceSession((previous) => {
      const nextProjectId = patch.project_id ?? previous.project_id;
      const nextSources =
        patch.attached_context_sources ??
        (nextProjectId
          ? ['thread-history', 'project-context', 'provider-runtime-catalog']
          : ['thread-history', 'provider-runtime-catalog']);

      return {
        ...previous,
        ...patch,
        attached_context_sources: nextSources,
      };
    });
    setRuntimeBinding((previous) =>
      previous.status === 'bound' ? { status: 'pending', error: null } : previous
    );
  }, []);

  const setCurrentMode = useCallback((mode: WorkspaceMode) => {
    setSessionPatch({ mode });
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [setSessionPatch]);

  const setCurrentProjectId = useCallback((projectId: string) => {
    setSessionPatch({ project_id: projectId });
  }, [setSessionPatch]);

  const setCurrentProvider = useCallback((providerId: string) => {
    const selected = providers.find((item) => item.id === providerId);
    if (!selected) {
      const message = `Provider '${providerId}' is not available from live runtime discovery.`;
      dispatch({ type: 'SET_ERROR', payload: message });
      setRuntimeBinding({ status: 'invalid', error: message });
      return;
    }

    if (['blocked', 'unavailable', 'not_configured'].includes(selected.status)) {
      const message = `Provider '${selected.name}' is ${selected.status} and cannot be bound.`;
      dispatch({ type: 'SET_ERROR', payload: message });
      setRuntimeBinding({ status: 'invalid', error: message });
      return;
    }

    const providerModels = modelsForProvider(models, providerId);
    const modelStillValid = providerModels.some((item: ModelInfo) => item.id === currentModel);
    setSessionPatch({ provider: providerId, model: modelStillValid ? currentModel : '' });
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [providers, models, currentModel, setSessionPatch]);

  const setCurrentModel = useCallback((modelId: string) => {
    if (!currentProvider) {
      const message = 'Select a provider before choosing a model.';
      dispatch({ type: 'SET_ERROR', payload: message });
      setRuntimeBinding({ status: 'invalid', error: message });
      return;
    }

    const providerModels = modelsForProvider(models, currentProvider);
    const selectedModel = providerModels.find((item: ModelInfo) => item.id === modelId);
    if (!selectedModel) {
      const message = `Model '${modelId}' is not available for provider '${currentProvider}'.`;
      dispatch({ type: 'SET_ERROR', payload: message });
      setRuntimeBinding({ status: 'invalid', error: message });
      return;
    }

    setSessionPatch({ model: modelId });
    dispatch({ type: 'SET_ERROR', payload: null });
  }, [currentProvider, models, setSessionPatch]);

  useEffect(() => {
    if (!activeThreadId) {
      return;
    }
    setWorkspaceSession((previous) => ({ ...previous, thread_id: activeThreadId }));
  }, [activeThreadId]);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const payload = (await callMCPTool('workbench.project_list')) as {
          success?: boolean;
          projects?: WorkbenchProject[];
        };

        if (payload.success === false) {
          setAvailableProjects([]);
          return;
        }

        setAvailableProjects(payload.projects || []);
      } catch {
        setAvailableProjects([]);
      }
    };

    void loadProjects();
  }, []);

  useEffect(() => {
    const refreshRuntimeState = async () => {
      const [mcpHealthy, llmHealthy] = await Promise.all([
        checkMCPBridgeHealth(),
        checkLLMProxyHealth(),
      ]);

      if (!mcpHealthy) {
        setAvailableTools([]);
        setRuntimeHealth({ mcpHealthy, llmHealthy, toolsAvailable: false });
        return;
      }

      const tools = await listTools();
      setAvailableTools(tools);
      setRuntimeHealth({
        mcpHealthy,
        llmHealthy,
        toolsAvailable: tools.length > 0,
      });
    };

    void refreshRuntimeState();
    const interval = setInterval(() => {
      void refreshRuntimeState();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!workspaceSession.provider && providers.length > 0) {
      const defaultProvider = providers.find(
        (item) => !['blocked', 'unavailable', 'not_configured'].includes(item.status)
      );
      if (defaultProvider) {
        setSessionPatch({ provider: defaultProvider.id });
      }
    }
  }, [providers, workspaceSession.provider, setSessionPatch]);

  useEffect(() => {
    if (!workspaceSession.provider) {
      return;
    }

    const providerModels = modelsForProvider(models, workspaceSession.provider);
    if (providerModels.length === 0) {
      if (workspaceSession.model) {
        setSessionPatch({ model: '' });
      }
      return;
    }

    if (!workspaceSession.model) {
      setSessionPatch({ model: providerModels[0].id });
    }
  }, [models, workspaceSession.provider, workspaceSession.model, setSessionPatch]);

  // Load messages from active thread on mount
  useEffect(() => {
    if (activeThreadId) {
      const thread = threadStore.threads.find(t => t.id === activeThreadId);
      if (thread) {
        if (thread.messages.length > 0) {
          const deserialized = deserializeMessages(thread.messages);
          deserialized.forEach(msg => dispatch({ type: 'ADD_MESSAGE', payload: msg }));
        }

        if (thread.workspaceSession) {
          setWorkspaceSession(thread.workspaceSession);
        } else {
          setWorkspaceSession((previous) => ({
            ...previous,
            thread_id: thread.id,
            provider: thread.provider || previous.provider,
            model: thread.model || previous.model,
            project_id: thread.projectId || previous.project_id,
          }));
        }
      }
    }
  }, []);

  // Save thread to storage when messages change
  const saveCurrentThread = useCallback(() => {
    if (!activeThreadId) return;
    
    const serialized = serializeMessages(state.messages);
    const metadata = buildRuntimeMetadata(workspaceSession) as RuntimeBindingMetadata;
    const updatedStore = updateThreadInStore(threadStore, activeThreadId, (thread) => ({
      ...thread,
      messages: serialized,
      provider: workspaceSession.provider || thread.provider,
      model: workspaceSession.model || thread.model,
      mode: workspaceSession.mode,
      projectId: workspaceSession.project_id || thread.projectId,
      workspaceSession,
      runtimeMetadata: metadata,
      lastProvider: workspaceSession.provider || thread.lastProvider,
      lastModel: workspaceSession.model || thread.lastModel,
      lastMode: workspaceSession.mode || thread.lastMode,
    }));
    
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
  }, [activeThreadId, threadStore, state.messages, workspaceSession]);

  // Auto-save when messages change (debounced)
  useEffect(() => {
    if (activeThreadId && state.messages.length > 0) {
      const timer = setTimeout(saveCurrentThread, 1000);
      return () => clearTimeout(timer);
    }
  }, [state.messages, activeThreadId, saveCurrentThread]);

  useEffect(() => {
    if (!activeThreadId) {
      return;
    }
    const timer = setTimeout(saveCurrentThread, 300);
    return () => clearTimeout(timer);
  }, [workspaceSession, activeThreadId, saveCurrentThread]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.streamingContent]);

  // Thread management functions
  const createThread = useCallback((
    titleOrOptions?: string | { title?: string; projectId?: string; folderPath?: string; inheritProjectContext?: boolean }
  ) => {
    const options = typeof titleOrOptions === 'string' ? { title: titleOrOptions } : titleOrOptions || {};
    const createdAt = new Date().toISOString();
    const targetProjectId = options.projectId ?? workspaceSession.project_id;
    const nextSession: ChatWorkspaceSession = {
      ...workspaceSession,
      thread_id: '',
      project_id: targetProjectId,
      attached_context_sources: options.inheritProjectContext && targetProjectId
        ? ['thread-history', 'project-context', 'provider-runtime-catalog']
        : ['thread-history', 'provider-runtime-catalog'],
    };
    const newThread: Thread = normalizeThread({
      id: uuidv4(),
      title: options.title || `Chat ${new Date().toLocaleDateString()}`,
      messages: [],
      createdAt,
      updatedAt: createdAt,
      created_at: createdAt,
      updated_at: createdAt,
      isPinned: false,
      isArchived: false,
      provider: workspaceSession.provider,
      model: workspaceSession.model,
      mode: workspaceSession.mode,
      projectId: targetProjectId,
      folderPath: options.folderPath || '',
      workspaceSession: nextSession,
      runtimeMetadata: buildRuntimeMetadata(nextSession) as RuntimeBindingMetadata,
      lastProvider: workspaceSession.provider,
      lastModel: workspaceSession.model,
      lastMode: workspaceSession.mode,
    });
    
    const updatedStore = {
      ...threadStore,
      threads: [newThread, ...threadStore.threads],
      activeThreadId: newThread.id,
    };
    
    setThreadStore(updatedStore);
    setActiveThreadId(newThread.id);
    setWorkspaceSession((previous) => ({ ...previous, thread_id: newThread.id }));
    saveThreadStore(updatedStore);
    dispatch({ type: 'CLEAR_MESSAGES' });
    
    return newThread;
  }, [threadStore, workspaceSession]);

  const loadThread = useCallback((threadId: string) => {
    const thread = threadStore.threads.find(t => t.id === threadId);
    if (!thread) return;
    
    // Save current thread first
    if (activeThreadId) {
      saveCurrentThread();
    }
    
    // Clear current messages and load new ones
    dispatch({ type: 'CLEAR_MESSAGES' });
    
    if (thread.messages.length > 0) {
      const deserialized = deserializeMessages(thread.messages as unknown[]);
      deserialized.forEach(msg => dispatch({ type: 'ADD_MESSAGE', payload: msg }));
    }
    
    // Update active thread and validate project context
    setActiveThreadId(threadId);
    
    let targetProjectId = '';
    if (thread.workspaceSession?.project_id) {
      setWorkspaceSession(thread.workspaceSession);
      targetProjectId = thread.workspaceSession.project_id;
    } else {
      targetProjectId = thread.projectId || '';
      setWorkspaceSession((previous) => ({
        ...previous,
        thread_id: threadId,
        provider: thread.provider || previous.provider,
        model: thread.model || previous.model,
        project_id: targetProjectId,
      }));
    }
    
    // Validate project context is still available
    if (targetProjectId) {
      const projectStillExists = availableProjects.some(p => p.project_id === targetProjectId);
      if (!projectStillExists) {
        console.warn(`Thread project ${targetProjectId} no longer available in project registry`);
      }
    }
    
    const updatedStore = { ...threadStore, activeThreadId: threadId };
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
  }, [threadStore, activeThreadId, saveCurrentThread, availableProjects]);

  const deleteThread = useCallback((threadId: string) => {
    const updatedStore = {
      ...threadStore,
      threads: threadStore.threads.filter(t => t.id !== threadId),
      activeThreadId: activeThreadId === threadId ? null : activeThreadId,
    };
    
    setThreadStore(updatedStore);
    if (activeThreadId === threadId) {
      setActiveThreadId(null);
      dispatch({ type: 'CLEAR_MESSAGES' });
    }
    saveThreadStore(updatedStore);
  }, [threadStore, activeThreadId]);

  const togglePinThread = useCallback((threadId: string) => {
    const updatedStore = updateThreadInStore(threadStore, threadId, (thread) => ({
      ...thread,
      isPinned: !thread.isPinned,
    }));

    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
  }, [threadStore]);

  const getThreads = useCallback(() => threadStore.threads, [threadStore]);
  const threadGroups = groupThreads(threadStore.threads, availableProjects);

  const getPinnedThreads = useCallback(() => threadGroups.pinned, [threadGroups]);

  const getRecentThreads = useCallback(() => threadGroups.recent, [threadGroups]);
  
  const getThreadsByProject = useCallback((projectId: string) => 
    threadStore.threads.filter(t => t.projectId === projectId), [threadStore]);

  const updateThreadTitle = useCallback((threadId: string, title: string) => {
    const { store: updatedStore } = renameThreadInStore(threadStore, threadId, title);
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
  }, [threadStore]);

  const moveThreadToProject = useCallback((threadId: string, projectId: string, folderPath = '') => {
    const { store: updatedStore } = moveThreadToProjectInStore(threadStore, threadId, projectId, folderPath);
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);

    if (threadId === activeThreadId) {
      setCurrentProjectId(projectId);
      if (folderPath) {
        setSessionPatch({ attached_context_sources: ['thread-history', 'project-context', 'provider-runtime-catalog'] });
      }
    }
  }, [threadStore, activeThreadId, setCurrentProjectId, setSessionPatch]);

  const archiveThread = useCallback((threadId: string) => {
    const { store: updatedStore } = setThreadArchivedState(threadStore, threadId, true);
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);

    if (threadId === activeThreadId) {
      setActiveThreadId(null);
      dispatch({ type: 'CLEAR_MESSAGES' });
    }
  }, [threadStore, activeThreadId]);

  const unarchiveThread = useCallback((threadId: string) => {
    const { store: updatedStore } = setThreadArchivedState(threadStore, threadId, false);
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
  }, [threadStore]);

  // Bulk selection functions
  const toggleBulkSelectMode = useCallback(() => {
    setIsBulkSelectMode((prev) => !prev);
    setSelectedThreadIds([]); // Clear selection when toggling mode
  }, []);

  const toggleThreadSelection = useCallback((threadId: string) => {
    setSelectedThreadIds((prev) =>
      prev.includes(threadId) ? prev.filter((id) => id !== threadId) : [...prev, threadId]
    );
  }, []);

  const clearThreadSelection = useCallback(() => {
    setSelectedThreadIds([]);
  }, []);

  const archiveSelectedThreads = useCallback(() => {
    let updatedStore = threadStore;
    for (const threadId of selectedThreadIds) {
      updatedStore = setThreadArchivedState(updatedStore, threadId, true).store;
    }
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
    clearThreadSelection();
    // If the active thread was archived, clear it
    if (activeThreadId && selectedThreadIds.includes(activeThreadId)) {
      setActiveThreadId(null);
      dispatch({ type: 'CLEAR_MESSAGES' });
    }
  }, [threadStore, selectedThreadIds, clearThreadSelection, activeThreadId]);

  const moveSelectedThreadsToProject = useCallback((projectId: string, folderPath = '') => {
    let updatedStore = threadStore;
    for (const threadId of selectedThreadIds) {
      updatedStore = moveThreadToProjectInStore(updatedStore, threadId, projectId, folderPath).store;
    }
    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
    clearThreadSelection();
    // If the active thread was moved, update its project context
    if (activeThreadId && selectedThreadIds.includes(activeThreadId)) {
      setCurrentProjectId(projectId);
      if (folderPath) {
        setSessionPatch({ attached_context_sources: ['thread-history', 'project-context', 'provider-runtime-catalog'] });
      }
    }
  }, [threadStore, selectedThreadIds, clearThreadSelection, activeThreadId, setCurrentProjectId, setSessionPatch]);

  const mergeThreads = useCallback(async (
    threadIdsToMerge: string[],
    newTitle: string,
    mergePolicy: { projectId?: string; folderPath?: string; archiveOriginals: boolean }
  ) => {
    if (threadIdsToMerge.length < 2) {
      dispatch({ type: 'SET_ERROR', payload: 'Select at least two threads to merge.' });
      return null;
    }

    // Check for project consistency across threads
    const projectsInvolved = Array.from(new Set(threadIdsToMerge.map(id => {
      const thread = threadStore.threads.find(t => t.id === id);
      return thread?.projectId || '';
    }).filter(Boolean)));

    let finalProjectId = mergePolicy.projectId || '';
    let folderPath = mergePolicy.folderPath || '';

    if (projectsInvolved.length > 1 && !mergePolicy.projectId) {
      dispatch({ type: 'SET_ERROR', payload: 'Multiple projects detected. Please choose a single project for the merged thread.' });
      return null;
    }

    if (projectsInvolved.length === 1) {
      finalProjectId = projectsInvolved[0];
    }

    const { store: updatedStore, newThread, error } = mergeThreadsInStore(
      threadStore,
      threadIdsToMerge,
      newTitle,
      { projectId: finalProjectId, folderPath, archiveOriginals: mergePolicy.archiveOriginals }
    );

    if (error) {
      dispatch({ type: 'SET_ERROR', payload: error });
      return null;
    }

    setThreadStore(updatedStore);
    saveThreadStore(updatedStore);
    clearThreadSelection();

    if (newThread) {
      loadThread(newThread.id);
      return newThread.id;
    }
    return null;
  }, [threadStore, clearThreadSelection, loadThread, dispatch]);

  const getRuntimeDegradedStates = useCallback((session: ChatWorkspaceSession) => {
    const projectContextAvailable = !session.project_id
      ? true
      : availableProjects.some((item) => item.project_id === session.project_id);

    return buildDegradedStateSummary({
      mcpHealthy: runtimeHealth.mcpHealthy,
      runtimeBinding,
      projectContextAvailable,
      toolsAvailable: runtimeHealth.toolsAvailable,
    });
  }, [availableProjects, runtimeHealth, runtimeBinding]);

  const appendOperatorAssistantMessage = useCallback((content: string, metadata: RuntimeBindingMetadata) => {
    const message: Message = {
      id: uuidv4(),
      role: 'assistant',
      content,
      timestamp: new Date(),
      runtimeMetadata: metadata,
    };
    dispatch({ type: 'ADD_MESSAGE', payload: message });
  }, []);

  const executeToolWithTrace = useCallback(
    async (toolName: string, args: Record<string, unknown>, metadata?: RuntimeBindingMetadata) => {
      const toolCallId = uuidv4();
      const toolMessage: Message = {
        id: uuidv4(),
        role: 'tool',
        content: `Running ${toolName}...`,
        timestamp: new Date(),
        runtimeMetadata: metadata,
        toolCalls: [
          {
            id: toolCallId,
            name: toolName,
            arguments: args,
            argumentsSummary: summarizeToolArguments(args),
            status: 'pending',
            timestamp: new Date(),
          },
        ],
      };

      dispatch({ type: 'ADD_MESSAGE', payload: toolMessage });

      if (!runtimeHealth.mcpHealthy) {
        dispatch({
          type: 'UPDATE_MESSAGE',
          payload: {
            id: toolMessage.id,
            updates: {
              content: 'Tool blocked: MCP bridge unavailable.',
              toolCalls: [
                {
                  ...toolMessage.toolCalls![0],
                  status: 'blocked',
                  result: {
                    output: 'MCP bridge unavailable',
                    duration: 0,
                    error: 'MCP bridge unavailable',
                  },
                },
              ],
            },
          },
        });
  const runtimeDegradedStates = getRuntimeDegradedStates(workspaceSession);

  return {
          success: false,
          blocked: true,
          error: 'MCP bridge unavailable',
        };
      }

      const result = await executeTool(toolName, args);
      const failureStatus = result.success ? 'success' : classifyToolFailure(result.error || '');

      dispatch({
        type: 'UPDATE_MESSAGE',
        payload: {
          id: toolMessage.id,
          updates: {
            content: result.success
              ? formatToolResult(result.result)
              : `${failureStatus === 'blocked' ? 'Blocked' : 'Error'}: ${result.error}`,
            toolCalls: [
              {
                ...toolMessage.toolCalls![0],
                status: result.success ? 'success' : failureStatus,
                result: {
                  output: (result.result as string | Record<string, unknown>) || result.error || 'No output',
                  duration: result.duration,
                  error: result.error,
                },
              },
            ],
          },
        },
      });

      return result;
    },
    [runtimeHealth.mcpHealthy]
  );

  const checkAndExecuteTools = useCallback(
    async (content: string, parentMessageId: string) => {
      // Check for explicit tool call syntax: <tool>name(args)</tool>
      const toolRegex = /<tool>(\w+)\((.*?)\)<\/tool>/g;
      let match;
      
      while ((match = toolRegex.exec(content)) !== null) {
        const toolName = match[1];
        const argsStr = match[2];
        
        try {
          const args = argsStr ? JSON.parse(argsStr) : {};
          await executeToolCall(toolName, args, parentMessageId);
        } catch {
          // Ignore parsing errors
        }
      }
    },
    []
  );

  const executeToolCall = useCallback(
    async (toolName: string, args: Record<string, unknown>, parentMessageId: string) => {
      void parentMessageId;
      return executeToolWithTrace(toolName, args, buildRuntimeMetadata(workspaceSession) as RuntimeBindingMetadata);
    },
    [executeToolWithTrace, workspaceSession]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() && state.attachedFiles.length === 0) return;

      let ensuredThreadId = activeThreadId;
      if (!ensuredThreadId) {
        const nextThread = createThread();
        ensuredThreadId = nextThread.id;
      }

      const candidateSession: ChatWorkspaceSession = {
        ...workspaceSession,
        thread_id: ensuredThreadId || '',
      };

      const bindingValidation = validateWorkspaceSessionBinding(
        candidateSession,
        providers,
        models
      );

      if (!bindingValidation.valid) {
        const errorMessage = bindingValidation.error || 'Invalid runtime binding.';
        setRuntimeBinding({ status: 'invalid', error: errorMessage });
        dispatch({ type: 'SET_ERROR', payload: errorMessage });
        return;
      }

      const boundSession: ChatWorkspaceSession = {
        ...bindingValidation.session,
        thread_id: ensuredThreadId || '',
        bound_at: new Date().toISOString(),
      };
      const boundMetadata: RuntimeBindingMetadata = {
        ...buildRuntimeMetadata(boundSession),
        mode: boundSession.mode,
      };

      setWorkspaceSession(boundSession);
      setRuntimeBinding({ status: 'bound', error: null });

      const [llmHealthy, mcpHealthy] = await Promise.all([
        checkLLMProxyHealth(),
        checkMCPBridgeHealth(),
      ]);
      setRuntimeHealth((previous) => ({
        ...previous,
        llmHealthy,
        mcpHealthy,
      }));

      // Create user message
      const userMessage: Message = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: new Date(),
        attachments: state.attachedFiles.length > 0 ? [...state.attachedFiles] : undefined,
        runtimeMetadata: boundMetadata,
      };

      dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
      dispatch({ type: 'SET_ERROR', payload: null });

      // Clear attachments after sending
      state.attachedFiles.forEach((file) => {
        dispatch({ type: 'REMOVE_ATTACHMENT', payload: file.id });
      });

      const intent = detectOperatorIntent(content);
      if (intent.type === 'introspection') {
        let toolsForResponse = availableTools;

        if ((intent.topic === 'tools' || intent.topic === 'runtime') && mcpHealthy) {
          // Use listTools() directly - tools.list is an RPC method, not a callable tool
          const liveTools = await listTools();
          toolsForResponse = liveTools;
          setAvailableTools(liveTools);
          setRuntimeHealth((previous) => ({ ...previous, toolsAvailable: liveTools.length > 0 }));
        }

        const activeProject = availableProjects.find((item) => item.project_id === boundSession.project_id) || null;
        const degradedStates = getRuntimeDegradedStates(boundSession);
        const introspection = buildRuntimeIntrospectionResponse({
          topic: intent.topic,
          session: boundSession,
          runtimeBinding,
          mcpHealthy,
          project: activeProject,
          toolPolicy: boundSession.tool_policy,
          availableTools: toolsForResponse,
          degradedStates,
        });

        appendOperatorAssistantMessage(introspection, boundMetadata);
        return;
      }

      if (intent.type === 'tool_action') {
        const result = await executeToolWithTrace(intent.tool, intent.arguments, boundMetadata);
        const resultText =
          result && typeof result === 'object' && 'success' in result && result.success
            ? `Operator tool run completed: ${intent.tool}`
            : `Operator tool run did not complete: ${intent.tool}`;
        appendOperatorAssistantMessage(resultText, boundMetadata);
        return;
      }

      if (!llmHealthy) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'LLM proxy unavailable. Ensure bazzite-llm-proxy.service is running on 127.0.0.1:8767.',
        });
        appendOperatorAssistantMessage(
          'LLM runtime is unavailable. Use Tools/Runtime actions while the proxy is down.',
          boundMetadata
        );
        return;
      }

      if (!mcpHealthy) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'MCP bridge unavailable. Tool execution is currently degraded on 127.0.0.1:8766.',
        });
      }
      
      // Create placeholder for assistant message
      const assistantMessageId = uuidv4();
      assistantIdRef.current = assistantMessageId;
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
        runtimeMetadata: boundMetadata,
      };

      dispatch({ type: 'ADD_MESSAGE', payload: assistantMessage });
      dispatch({ type: 'SET_STREAMING', payload: true });
      dispatch({ type: 'CLEAR_STREAMING_CONTENT' });
      streamingContentRef.current = '';

      try {
        // Get all messages for context
        const runtimeSystemMessage: Message = {
          id: uuidv4(),
          role: 'system',
          content: getRuntimeSystemPrompt(boundSession),
          timestamp: new Date(),
        };

        const allMessages = [runtimeSystemMessage, ...state.messages, userMessage];
        
        // Start streaming
        const abort = await streamChatCompletion(
          allMessages,
          {
            onChunk: (chunk) => {
              streamingContentRef.current += chunk;
              dispatch({ type: 'APPEND_STREAMING_CONTENT', payload: chunk });
            },
            onComplete: (fullResponse) => {
              streamingContentRef.current = '';
              dispatch({ type: 'SET_STREAMING', payload: false });
              dispatch({
                type: 'UPDATE_MESSAGE',
                payload: {
                  id: assistantMessageId,
                  updates: {
                    content: fullResponse,
                    isStreaming: false,
                    runtimeMetadata: boundMetadata,
                  },
                },
              });
              dispatch({ type: 'CLEAR_STREAMING_CONTENT' });
              
              // Check for tool calls in the response
              checkAndExecuteTools(fullResponse, assistantMessageId);
            },
            onError: (error) => {
              const partialContent = streamingContentRef.current;
              streamingContentRef.current = '';
              dispatch({ type: 'SET_STREAMING', payload: false });
              dispatch({
                type: 'UPDATE_MESSAGE',
                payload: {
                  id: assistantMessageId,
                  updates: {
                    content: partialContent || 'Error: Failed to get response',
                    isStreaming: false,
                    error: error.message,
                    runtimeMetadata: boundMetadata,
                  },
                },
              });
              dispatch({ type: 'SET_ERROR', payload: error.message });
            },
            onToolCall: async (toolName, args) => {
              // Execute tool automatically
              await executeToolCall(toolName, args, assistantMessageId);
            },
          },
          {
            model: boundSession.model,
            runtimeBinding: {
              threadId: boundSession.thread_id,
              projectId: boundSession.project_id,
              mode: boundSession.mode,
              provider: boundSession.provider,
              model: boundSession.model,
              memoryPolicy: boundSession.memory_policy,
              toolPolicy: boundSession.tool_policy,
              attachedContextSources: boundSession.attached_context_sources,
            },
          }
        );

        abortControllerRef.current = abort;
      } catch (error) {
        dispatch({ type: 'SET_STREAMING', payload: false });
        dispatch({
          type: 'UPDATE_MESSAGE',
          payload: {
            id: assistantMessageId,
            updates: {
              content: 'Error: Failed to start streaming',
              isStreaming: false,
              error: error instanceof Error ? error.message : 'Unknown error',
            },
          },
        });
      }
    },
    [
      state.messages,
      state.attachedFiles,
      activeThreadId,
      workspaceSession,
      providers,
      models,
      createThread,
      getRuntimeSystemPrompt,
      checkAndExecuteTools,
      executeToolCall,
      executeToolWithTrace,
      appendOperatorAssistantMessage,
      availableProjects,
      availableTools,
      getRuntimeDegradedStates
    ]
  );

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    // Finalize the current assistant message with whatever content was streamed
    const partialContent = streamingContentRef.current;
    if (partialContent && assistantIdRef.current) {
      dispatch({
        type: 'UPDATE_MESSAGE',
        payload: {
          id: assistantIdRef.current,
          updates: {
            content: partialContent,
            isStreaming: false,
          },
        },
      });
      streamingContentRef.current = '';
      assistantIdRef.current = null;
    }
    dispatch({ type: 'SET_STREAMING', payload: false });
    dispatch({ type: 'CLEAR_STREAMING_CONTENT' });
  }, []);

  const addAttachment = useCallback((file: File) => {
    const attachment: Attachment = {
      id: uuidv4(),
      name: file.name,
      type: file.type,
      size: file.size,
    };

    // For images, create a preview
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        attachment.previewUrl = e.target?.result as string;
        dispatch({ type: 'ADD_ATTACHMENT', payload: attachment });
      };
      reader.readAsDataURL(file);
    } else {
      dispatch({ type: 'ADD_ATTACHMENT', payload: attachment });
    }
  }, []);

  const removeAttachment = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_ATTACHMENT', payload: id });
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  const runtimeDegradedStates = getRuntimeDegradedStates(workspaceSession);

  const operatorActionSurface = getOperatorActionSurface({
    toolPolicy: workspaceSession.tool_policy,
  });

  const runOperatorAction = useCallback((actionCommand: string) => {
    void sendMessage(actionCommand);
  }, [sendMessage]);

  return {
    messages: state.messages,
    isStreaming: state.isStreaming,
    streamingContent: state.streamingContent,
    attachedFiles: state.attachedFiles,
    contextPins: state.contextPins,
    tokenUsage: state.tokenUsage,
    error: state.error,
    taskType: workspaceSession.mode,
    sendMessage,
    stopGeneration,
    addAttachment,
    removeAttachment,
    clearMessages,
    messagesEndRef,
    // Thread management
    threads: getThreads(),
    pinnedThreads: getPinnedThreads(),
    recentThreads: getRecentThreads(),
    groupedThreadsByProject: threadGroups.byProject,
    archivedThreads: threadGroups.archived,
    activeThreadId,
    createThread,
    loadThread,
    deleteThread,
    togglePinThread,
    renameThread: updateThreadTitle,
    updateThreadTitle,
    moveThreadToProject,
    archiveThread,
    unarchiveThread,
    getThreadsByProject,
    projects: availableProjects,
    workspaceSession,
    runtimeBinding,
    runtimeHealth,
    availableTools,
    runtimeDegradedStates,
    operatorActionSurface,
    runOperatorAction,
    // Context controls
    currentProvider,
    setCurrentProvider,
    currentMode: workspaceSession.mode,
    setCurrentMode,
    currentModel,
    setCurrentModel,
    currentProjectId,
    setCurrentProjectId,
    // Bulk selection and merge
    isBulkSelectMode,
    selectedThreadIds,
    toggleBulkSelectMode,
    toggleThreadSelection,
    clearThreadSelection,
    mergeThreads,
    moveSelectedThreadsToProject,
    archiveSelectedThreads,
  };
}