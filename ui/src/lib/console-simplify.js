export function buildHomeSystemStatus({
  securitySummary,
  runtimeSummary,
  securityLoading,
  providersLoading,
  securityError,
  providersError,
  partialData,
  missingSources,
}) {
  const securityStatus = String(securitySummary?.status || 'unknown').toLowerCase();
  const hasCritical = Number(securitySummary?.critical || 0) > 0;
  const hasHigh = Number(securitySummary?.high || 0) > 0;
  const hasRuntimeIssues = Number(runtimeSummary?.degraded || 0) > 0 || Number(runtimeSummary?.blocked || 0) > 0;
  const hasErrors = Boolean(securityError || providersError);

  let tone = 'neutral';
  if (hasErrors || securityStatus.includes('critical') || hasCritical) {
    tone = 'danger';
  } else if (securityStatus.includes('warning') || hasHigh || hasRuntimeIssues || partialData) {
    tone = 'warning';
  } else if (securityStatus.includes('secure') || securityStatus.includes('healthy') || securityStatus.includes('ok')) {
    tone = 'success';
  }

  const details = [
    `${securityLoading ? 'Refreshing' : 'Security'}: ${securitySummary?.alerts ?? 0} alerts / ${securitySummary?.findings ?? 0} findings`,
    `${providersLoading ? 'Refreshing' : 'Runtime'}: ${runtimeSummary?.healthy ?? 0} healthy / ${runtimeSummary?.degraded ?? 0} degraded / ${runtimeSummary?.blocked ?? 0} blocked`,
  ];

  if (partialData && Array.isArray(missingSources) && missingSources.length > 0) {
    details.push(`Partial data: ${missingSources.join(', ')}`);
  }
  if (securityError) {
    details.push(`Security error: ${securityError}`);
  }
  if (providersError) {
    details.push(`Runtime error: ${providersError}`);
  }

  return {
    tone,
    title: tone === 'danger' ? 'Attention required' : tone === 'warning' ? 'Watch state' : 'Healthy',
    details,
  };
}

export function buildRuntimeStrip({
  workspaceSession,
  runtimeBinding,
  currentLocationLabel,
  runtimeHealth,
  availableTools,
  degradedStates,
}) {
  const provider = workspaceSession?.provider || 'none';
  const model = workspaceSession?.model || 'none';
  const mode = workspaceSession?.mode || 'fast';
  const project = workspaceSession?.project_id || 'no-project';

  const bindingState = runtimeBinding?.status || 'pending';
  const statusTone = bindingState === 'bound' ? 'success' : bindingState === 'invalid' ? 'danger' : 'warning';

  return {
    summary: `${provider} / ${model} / ${mode} / ${project}`,
    location: currentLocationLabel || 'No active thread',
    status: bindingState === 'bound' ? 'Bound' : bindingState === 'invalid' ? 'Invalid selection' : 'Pending bind',
    statusTone,
    details: [
      `MCP: ${runtimeHealth?.mcpHealthy ? 'healthy' : 'degraded'}`,
      `LLM: ${runtimeHealth?.llmHealthy ? 'healthy' : 'degraded'}`,
      `Tools: ${Array.isArray(availableTools) ? availableTools.length : 0}`,
      `Policy: ${workspaceSession?.tool_policy || 'unknown'}`,
    ],
    degraded: Array.isArray(degradedStates) ? degradedStates : [],
  };
}

export function getThreadActionItems(thread) {
  return [
    { id: 'rename', label: 'Rename' },
    { id: 'move', label: 'Move' },
    {
      id: thread?.isArchived ? 'restore' : 'archive',
      label: thread?.isArchived ? 'Restore' : 'Archive',
    },
    { id: 'delete', label: 'Delete' },
  ];
}
