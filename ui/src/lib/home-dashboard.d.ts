export const THREADS_STORAGE_KEY: string;

export type HomeThreadSummary = {
  id: string;
  title: string;
  updatedAt: string;
  projectId: string;
  folderPath: string;
  mode: string;
  provider: string;
  model: string;
  isPinned: boolean;
};

export function extractRecentThreads(
  store: { threads?: unknown[]; activeThreadId?: string | null } | null,
  limit?: number
): HomeThreadSummary[];

export function markThreadActive(
  store: { version?: number; threads?: unknown[]; activeThreadId?: string | null } | null,
  threadId: string
): { version: number; threads: unknown[]; activeThreadId: string } | { version?: number; threads?: unknown[]; activeThreadId: string };

export function buildProjectRegisterArgs(input: {
  name?: string;
  path?: string;
  description?: string;
  tags?: string;
}): {
  name: string;
  path: string;
  description: string;
  tags: string;
  allow_non_project_dirs: false;
};

export function summarizeRuntimeOverview(
  counts: {
    total?: number;
    configured?: number;
    healthy?: number;
    degraded?: number;
    blocked?: number;
  } | null,
  providers: Array<{ is_configured?: boolean; is_healthy?: boolean; status?: string; is_local?: boolean }> | null,
  models: Array<{ is_available?: boolean }> | null
): {
  totalProviders: number;
  totalModels: number;
  configured: number;
  healthy: number;
  degraded: number;
  blocked: number;
  localProviders: number;
};

export function summarizeSecurityWidget(
  overview: {
    system_status?: string;
    critical_count?: number;
    high_count?: number;
    medium_count?: number;
    low_count?: number;
    last_scan_time?: string | null;
  } | null,
  alerts: unknown[] | null,
  findings: unknown[] | null,
  systemHealth: { health_status?: string; state?: string; last_scan?: string | null } | null
): {
  status: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  alerts: number;
  findings: number;
  lastScan: string | null;
};
