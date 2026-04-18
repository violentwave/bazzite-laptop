import { ChatWorkspaceSession } from '@/types/chat';

export function summarizeToolArguments(args: Record<string, unknown>): string;
export function classifyToolFailure(errorText: string): 'blocked' | 'error';

export function detectOperatorIntent(text: string):
  | { type: 'none' }
  | { type: 'introspection'; topic: string; source: string }
  | { type: 'tool_action'; tool: string; arguments: Record<string, unknown> };

export function buildDegradedStateSummary(input: {
  mcpHealthy: boolean;
  runtimeBinding: { status: string; error: string | null };
  projectContextAvailable: boolean;
  toolsAvailable: boolean;
}): string[];

export function buildRuntimeIntrospectionResponse(input: {
  topic: string;
  session: ChatWorkspaceSession;
  runtimeBinding: { status: string; error: string | null };
  mcpHealthy: boolean;
  project: { name?: string; root_path?: string } | null;
  toolPolicy: string;
  availableTools: string[];
  degradedStates: string[];
}): string;

export function getOperatorActionSurface(runtime: {
  toolPolicy: string;
}): Array<{ id: string; label: string; command: string; enabled: boolean }>;
