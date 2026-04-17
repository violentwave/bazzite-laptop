export type WorkbenchBackend = "opencode" | "codex" | "claude-code" | "gemini-cli";

export type WorkbenchSessionStatus = "active" | "stopped" | "expired";

export type WorkbenchSandboxProfile = "conservative" | "analysis";

export interface WorkbenchProject {
  project_id: string;
  name: string;
  root_path: string;
  created_at: string;
  updated_at: string;
  last_opened_at?: string | null;
  tags: string[];
  description: string;
}

export interface WorkbenchSession {
  session_id: string;
  project_id: string;
  backend: WorkbenchBackend;
  cwd: string;
  status: WorkbenchSessionStatus;
  sandbox_profile: WorkbenchSandboxProfile;
  created_at: string;
  updated_at: string;
  expires_at?: string | null;
}

export interface WorkbenchProjectStatus {
  project: WorkbenchProject;
  exists: boolean;
  is_dir: boolean;
  allowed_roots: string[];
}

export interface WorkbenchGitFileChange {
  path: string;
  status: string;
}

export interface WorkbenchGitStatus {
  is_git_repo: boolean;
  branch: string;
  is_dirty: boolean;
  ahead: number;
  behind: number;
  recent_commit: string;
  staged_count: number;
  unstaged_count: number;
  untracked_count: number;
  changed_files: WorkbenchGitFileChange[];
  staged_diff_stat: string;
  unstaged_diff_stat: string;
}

export interface WorkbenchTestCommand {
  name: string;
  command: string[];
  description: string;
  timeout_seconds: number;
  enabled: boolean;
}

export interface WorkbenchTestExecution {
  success: boolean;
  command: WorkbenchTestCommand;
  exit_code: number;
  output: string;
}

export interface WorkbenchHandoffNote {
  timestamp: string;
  phase: string;
  summary: string;
  artifacts: string[];
  session_id?: string | null;
}

export interface WorkbenchAgentProfile {
  id: WorkbenchBackend;
  label: string;
  mode: "bounded" | "manual-approval";
  shell_access: boolean;
  network_access: boolean;
  allowed_tools: string[];
  notes: string;
}
