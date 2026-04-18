import { ChatWorkspaceSession } from '@/types/chat';

export function buildHomeSystemStatus(input: {
  securitySummary: {
    status: string;
    critical: number;
    high: number;
    alerts: number;
    findings: number;
  };
  runtimeSummary: {
    healthy: number;
    degraded: number;
    blocked: number;
  };
  securityLoading: boolean;
  providersLoading: boolean;
  securityError: string | null;
  providersError: string | null;
  partialData: boolean;
  missingSources: string[];
}): {
  tone: 'success' | 'warning' | 'danger' | 'neutral';
  title: string;
  details: string[];
};

export function buildRuntimeStrip(input: {
  workspaceSession: ChatWorkspaceSession;
  runtimeBinding: { status: string; error: string | null };
  currentLocationLabel: string;
  runtimeHealth: { mcpHealthy: boolean; llmHealthy: boolean };
  availableTools: string[];
  degradedStates: string[];
}): {
  summary: string;
  location: string;
  status: string;
  statusTone: 'success' | 'warning' | 'danger';
  details: string[];
  degraded: string[];
};

export function getThreadActionItems(thread: { isArchived?: boolean }): Array<{
  id: 'rename' | 'move' | 'archive' | 'restore' | 'delete';
  label: string;
}>;
