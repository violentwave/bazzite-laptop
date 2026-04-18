/**
 * Chat Workspace Types
 * P80 - Chat Workspace, P140 - Thread Persistence
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  attachments?: Attachment[];
  isStreaming?: boolean;
  error?: string;
  runtimeMetadata?: RuntimeBindingMetadata;
  sourceThreadIds?: string[]; // New: for merged threads, tracks original thread IDs
}

export type WorkspaceMode = 'fast' | 'reason' | 'batch' | 'code' | 'embed';

export type ProjectHydrationState = 'selected' | 'hydrating' | 'hydrated' | 'unavailable' | 'invalid';

export interface RuntimeBindingMetadata {
  provider: string;
  model: string;
  mode: WorkspaceMode;
  project_id: string;
  project_hydration_state?: ProjectHydrationState; // New: tracks project context availability
  memory_policy: string;
  tool_policy: string;
  attached_context_sources: string[];
  bound_at: string;
}

export interface ChatWorkspaceSession {
  thread_id: string;
  project_id: string;
  mode: WorkspaceMode;
  provider: string;
  model: string;
  memory_policy: string;
  tool_policy: string;
  attached_context_sources: string[];
  bound_at: string;
}

export interface Thread {
  id: string;
  title: string;
  messages: unknown[]; // Serialized format for localStorage
  projectId?: string;
  folderPath?: string;
  createdAt: string;
  updatedAt: string;
  created_at?: string;
  updated_at?: string;
  isPinned: boolean;
  isArchived?: boolean;
  isMerged?: boolean; // New: indicates if this thread is a result of a merge
  provider?: string;
  model?: string;
  mode?: WorkspaceMode;
  lastProvider?: string;
  lastModel?: string;
  lastMode?: WorkspaceMode;
  taskType?: string;
  workspaceSession?: ChatWorkspaceSession;
  runtimeMetadata?: RuntimeBindingMetadata;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  argumentsSummary?: string;
  result?: ToolResult;
  status: 'pending' | 'success' | 'error' | 'blocked';
  timestamp: Date;
}

export interface ToolResult {
  output: string | Record<string, unknown>;
  duration: number;
  error?: string;
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  content?: string; // base64 for images
  previewUrl?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  tokenUsage: TokenUsage;
  contextPins: ContextPin[];
}

export interface TokenUsage {
  input: number;
  output: number;
  total: number;
}

export interface ContextPin {
  id: string;
  type: 'file' | 'search' | 'code' | 'tool-result';
  title: string;
  content: string;
  timestamp: Date;
}

export interface StreamingState {
  isStreaming: boolean;
  content: string;
  model: string;
  canStop: boolean;
}

export interface MCPRequest {
  tool: string;
  params: Record<string, unknown>;
}

export interface MCPResponse {
  success: boolean;
  result?: unknown;
  error?: string;
  duration: number;
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentConversationId: string | null;
  attachedFiles: Attachment[];
  contextPins: ContextPin[];
  tokenUsage: TokenUsage;
  error: string | null;
}

export type ChatAction =
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: { id: string; updates: Partial<Message> } }
  | { type: 'DELETE_MESSAGE'; payload: string }
  | { type: 'SET_STREAMING'; payload: boolean }
  | { type: 'UPDATE_STREAMING_CONTENT'; payload: string }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'SET_CONVERSATION'; payload: string }
  | { type: 'ADD_ATTACHMENT'; payload: Attachment }
  | { type: 'REMOVE_ATTACHMENT'; payload: string }
  | { type: 'ADD_CONTEXT_PIN'; payload: ContextPin }
  | { type: 'REMOVE_CONTEXT_PIN'; payload: string }
  | { type: 'SET_ERROR'; payload: string | null };
