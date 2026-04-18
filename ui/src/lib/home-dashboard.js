import { groupThreads } from './thread-store.js';

export const THREADS_STORAGE_KEY = 'bazzite-chat-threads';
export const CHAT_SELECTED_PROJECT_KEY = 'bazzite-chat-selected-project';

export function extractRecentThreads(store, limit = 6) {
  if (!store || typeof store !== 'object') {
    return [];
  }

  const threads = Array.isArray(store.threads) ? store.threads : [];
  const nonArchivedThreads = threads.filter(thread => !thread.isArchived);

  // Sort all non-archived threads by updatedAt descending
  const sortedThreads = [...nonArchivedThreads].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  );

  return sortedThreads.slice(0, limit).map((thread) => ({
    id: thread.id,
    title: thread.title,
    updatedAt: thread.updatedAt,
    projectId: thread.projectId || '',
    folderPath: thread.folderPath || '',
    mode: thread.lastMode || thread.mode || 'fast',
    provider: thread.lastProvider || thread.provider || '',
    model: thread.lastModel || thread.model || '',
    isPinned: Boolean(thread.isPinned),
  }));
}

export function markThreadActive(store, threadId) {
  if (!store || typeof store !== 'object') {
    return {
      version: 2,
      threads: [],
      activeThreadId: threadId,
    };
  }

  return {
    ...store,
    activeThreadId: threadId,
  };
}

export function buildProjectRegisterArgs(input) {
  const name = String(input?.name || '').trim();
  const path = String(input?.path || '').trim();
  const description = String(input?.description || '').trim();
  const tags = String(input?.tags || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

  return {
    name,
    path,
        description,
    tags,
  };
}

export function summarizeRuntimeOverview(counts, providers, models) {
  const safeProviders = Array.isArray(providers) ? providers : [];
  const safeModels = Array.isArray(models) ? models : [];

  const configured = counts?.configured ?? safeProviders.filter((item) => item.is_configured).length;
  const healthy = counts?.healthy ?? safeProviders.filter((item) => item.is_healthy).length;
  const degraded =
    counts?.degraded ?? safeProviders.filter((item) => item.status === 'degraded').length;
  const blocked = counts?.blocked ?? safeProviders.filter((item) => item.status === 'blocked').length;

  return {
    totalProviders: counts?.total ?? safeProviders.length,
    totalModels: safeModels.filter((item) => item.is_available !== false).length,
    configured,
    healthy,
    degraded,
    blocked,
    localProviders: safeProviders.filter((item) => item.is_local).length,
  };
}

export function summarizeSecurityWidget(overview, alerts, findings, systemHealth) {
  return {
    status:
      overview?.system_status ||
      systemHealth?.health_status ||
      systemHealth?.state ||
      'unknown',
    critical: overview?.critical_count ?? 0,
    high: overview?.high_count ?? 0,
    medium: overview?.medium_count ?? 0,
    low: overview?.low_count ?? 0,
    alerts: Array.isArray(alerts) ? alerts.length : 0,
    findings: Array.isArray(findings) ? findings.length : 0,
    lastScan: overview?.last_scan_time || systemHealth?.last_scan || null,
  };
}
