/**
 * Operator runtime helpers for grounded chat behavior.
 * Includes project hydration state model and compact degraded rendering.
 */

const INTROSPECTION_PATTERNS = [
  { topic: 'provider_model', pattern: /(provider|model).*(running|active)|what .*provider|what .*model/i },
  { topic: 'project', pattern: /what .*project|which project|where am i|current project/i },
  { topic: 'tools', pattern: /what .*tools|list tools|available tools|tool(s)? do you have/i },
  { topic: 'mode', pattern: /what .*mode|current mode|which mode/i },
  { topic: 'runtime', pattern: /runtime|session state|operator state/i },
];

const COMMAND_MAP = {
  '/runtime': 'runtime',
  '/tools': 'tools',
  '/project': 'project',
  '/mode': 'mode',
  '/provider': 'provider_model',
  '/memory': 'memory',
  '/files': 'files',
};

export function summarizeToolArguments(args) {
  if (!args || typeof args !== 'object') {
    return '{}';
  }
  const entries = Object.entries(args).slice(0, 3);
  const summary = entries
    .map(([key, value]) => {
      if (typeof value === 'string') {
        return `${key}=${value.length > 40 ? `${value.slice(0, 40)}...` : value}`;
      }
      if (typeof value === 'number' || typeof value === 'boolean') {
        return `${key}=${String(value)}`;
      }
      if (Array.isArray(value)) {
        return `${key}=[${value.length}]`;
      }
      return `${key}={...}`;
    })
    .join(', ');

  return summary || '{}';
}

export function classifyToolFailure(errorText) {
  const normalized = String(errorText || '').toLowerCase();
  if (
    normalized.includes('blocked') ||
    normalized.includes('policy') ||
    normalized.includes('approval') ||
    normalized.includes('not allowed')
  ) {
    return 'blocked';
  }
  return 'error';
}

export function detectOperatorIntent(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) {
    return { type: 'none' };
  }

  const command = trimmed.split(/\s+/)[0].toLowerCase();
  if (COMMAND_MAP[command]) {
    return { type: 'introspection', topic: COMMAND_MAP[command], source: 'command' };
  }

  for (const rule of INTROSPECTION_PATTERNS) {
    if (rule.pattern.test(trimmed)) {
      return { type: 'introspection', topic: rule.topic, source: 'natural-language' };
    }
  }

  if (/run security audit|security audit/i.test(trimmed)) {
    return { type: 'tool_action', tool: 'agents.security_audit', arguments: {} };
  }

  if (/system health|health check/i.test(trimmed)) {
    return { type: 'tool_action', tool: 'system.metrics_summary', arguments: { hours: 24 } };
  }

  return { type: 'none' };
}

/**
 * Build a compact degraded-state summary for display.
 * Returns array of human-readable degraded-state messages.
 */
export function buildDegradedStateSummary({
  mcpHealthy,
  runtimeBinding,
  projectContextAvailable,
  projectHydrationState,
  toolsAvailable,
}) {
  const issues = [];
  if (!mcpHealthy) {
    issues.push('MCP bridge unavailable');
  }
  if (runtimeBinding?.status === 'invalid') {
    issues.push('Runtime binding invalid');
  }
  if (projectHydrationState === 'unavailable') {
    issues.push('Project context unavailable');
  }
  if (projectHydrationState === 'invalid') {
    issues.push('Project context invalid');
  }
  if (projectHydrationState === 'hydrating') {
    issues.push('Project context loading');
  }
  if (!toolsAvailable) {
    issues.push('No tools available');
  }
  return issues;
}

/**
 * Build a compact degraded-state badge for runtime UI.
 * Returns a single condensed string representation.
 */
export function buildCompactDegradedBadge(degradedStates) {
  if (!degradedStates || degradedStates.length === 0) {
    return null;
  }
  // For 1–2 issues, show them. For 3+, show count.
  if (degradedStates.length <= 2) {
    return degradedStates.join(' • ');
  }
  return `${degradedStates.length} issues`;
}

export function buildRuntimeIntrospectionResponse({
  topic,
  session,
  runtimeBinding,
  projectHydrationState,
  mcpHealthy,
  project,
  toolPolicy,
  availableTools,
  degradedStates,
}) {
  const base = {
    provider: session.provider || 'none',
    model: session.model || 'none',
    mode: session.mode || 'none',
    project: project?.name || session.project_id || 'none',
    projectRoot: project?.root_path || 'unknown',
    projectStatus: projectHydrationState || 'unknown',
    toolPolicy: toolPolicy || session.tool_policy || 'unknown',
    memoryPolicy: session.memory_policy || 'unknown',
    runtimeStatus: runtimeBinding?.status || 'pending',
    mcpStatus: mcpHealthy ? 'healthy' : 'degraded',
  };

  const header = 'Operator runtime truth (active workspace session):';

  if (topic === 'tools') {
    const toolPreview = (availableTools || []).slice(0, 20);
    return [
      header,
      `- MCP status: ${base.mcpStatus}`,
      `- Tool policy: ${base.toolPolicy}`,
      `- Discovered tools: ${availableTools.length}`,
      `- Tool sample: ${toolPreview.length > 0 ? toolPreview.join(', ') : 'none'}`,
      ...(degradedStates.length ? [`- Degraded: ${degradedStates.join(' • ')}`] : []),
    ].join('\n');
  }

  if (topic === 'project' || topic === 'files') {
    return [
      header,
      `- Project: ${base.project}`,
      `- Project root: ${base.projectRoot}`,
      `- Project status: ${base.projectStatus}`,
      `- Runtime mode: ${base.mode}`,
      `- Memory policy: ${base.memoryPolicy}`,
      ...(degradedStates.length ? [`- Degraded: ${degradedStates.join(' • ')}`] : []),
    ].join('\n');
  }

  if (topic === 'mode') {
    return [
      header,
      `- Mode: ${base.mode}`,
      `- Provider: ${base.provider}`,
      `- Model: ${base.model}`,
      `- Tool policy: ${base.toolPolicy}`,
      ...(degradedStates.length ? [`- Degraded: ${degradedStates.join(' • ')}`] : []),
    ].join('\n');
  }

  return [
    header,
    `- Provider: ${base.provider}`,
    `- Model: ${base.model}`,
    `- Mode: ${base.mode}`,
    `- Project: ${base.project}`,
    `- Project status: ${base.projectStatus}`,
    `- Runtime binding: ${base.runtimeStatus}`,
    `- MCP: ${base.mcpStatus}`,
    `- Tool policy: ${base.toolPolicy}`,
    `- Memory policy: ${base.memoryPolicy}`,
    ...(degradedStates.length ? [`- Degraded: ${degradedStates.join(' • ')}`] : []),
  ].join('\n');
}

export function getOperatorActionSurface(runtime) {
  return [
    { id: 'tools', label: 'Tools', command: '/tools', enabled: true },
    { id: 'project', label: 'Project', command: '/project', enabled: true },
    { id: 'memory', label: 'Memory', command: '/memory', enabled: true },
    { id: 'files', label: 'Files', command: '/files', enabled: true },
    { id: 'runtime', label: 'Runtime', command: '/runtime', enabled: true },
    {
      id: 'policy',
      label: `Policy: ${runtime?.toolPolicy || 'unknown'}`,
      command: '/runtime',
      enabled: true,
    },
  ];
}
