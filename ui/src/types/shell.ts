/** Interactive Shell Gateway types */

export type SessionStatus = "active" | "idle" | "disconnected" | "error";

/** Shell session data structure */
export interface ShellSession {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  status: SessionStatus;
  cwd: string;
  pid: number | null;
  command_history: string[];
  metadata: Record<string, unknown>;
}

/** Session context for audit/display */
export interface SessionContext {
  session_id: string;
  user: string;
  hostname: string;
  cwd: string;
  shell: string;
  start_time: string;
  idle_time: number; // seconds
}

/** Command execution result */
export interface CommandResult {
  success: boolean;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
  error?: string;
  error_detail?: string;
  operator_action?: string;
}

/** Audit log entry */
export interface AuditLogEntry {
  timestamp: string;
  action: string;
  session_id: string;
  details: Record<string, unknown>;
}

/** Terminal output line */
export interface TerminalOutput {
  type: "input" | "output" | "error" | "system";
  content: string;
  timestamp: string;
}

/** Session with extended UI state */
export interface SessionUIState {
  session: ShellSession;
  context: SessionContext | null;
  output: TerminalOutput[];
  isLoading: boolean;
  error: string | null;
}

/** Shell tool result */
export interface ShellToolResult {
  success: boolean;
  result?: unknown;
  error?: string;
}
