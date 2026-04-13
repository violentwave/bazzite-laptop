/**
 * Provider and Model Types
 * P82 — Provider + Model Discovery / Routing Console
 */

export type ProviderStatus = 'healthy' | 'degraded' | 'blocked' | 'unavailable' | 'not_configured';

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  task_types: string[];
  is_available: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  status: ProviderStatus;
  is_configured: boolean;
  is_healthy: boolean;
  is_local: boolean;
  models: ModelInfo[];
  health_score: number;
  last_error: string | null;
  last_probe_time: number | null;
}

export interface RoutingEntry {
  task_type: string;
  task_label: string;
  primary_provider: string | null;
  fallback_chain: string[];
  eligible_models: ModelInfo[];
  health_state: string;
  caveats: string | null;
}

export interface ProviderHealth {
  score: number;
  success_count: number;
  failure_count: number;
  consecutive_failures: number;
  is_disabled: boolean;
  auth_broken: boolean;
}

export type TaskType = 'fast' | 'reason' | 'batch' | 'code' | 'embed';

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  fast: 'Fast (Interactive)',
  reason: 'Reason (Analysis)',
  batch: 'Batch (Volume)',
  code: 'Code (Generation)',
  embed: 'Embed (Vectors)',
};

export const TASK_TYPE_DESCRIPTIONS: Record<TaskType, string> = {
  fast: 'Speed-first for interactive chat and quick queries',
  reason: 'Reasoning-first for deep analysis and complex problems',
  batch: 'Volume-first for processing large amounts of data',
  code: 'Code-specialized models for programming tasks',
  embed: 'Embedding models for vector generation',
};
