import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildHomeSystemStatus,
  buildRuntimeStrip,
  getThreadActionItems,
} from './console-simplify.js';

test('buildHomeSystemStatus returns warning for degraded runtime', () => {
  const model = buildHomeSystemStatus({
    securitySummary: { status: 'secure', critical: 0, high: 0, alerts: 1, findings: 2 },
    runtimeSummary: { healthy: 2, degraded: 1, blocked: 0 },
    securityLoading: false,
    providersLoading: false,
    securityError: null,
    providersError: null,
    partialData: false,
    missingSources: [],
  });

  assert.equal(model.tone, 'warning');
  assert.match(model.details[1], /degraded/);
});

test('buildRuntimeStrip preserves runtime truth fields', () => {
  const strip = buildRuntimeStrip({
    workspaceSession: {
      thread_id: 't1',
      project_id: 'bazzite-laptop',
      mode: 'reason',
      provider: 'openai',
      model: 'gpt-4o-mini',
      memory_policy: 'project-bound',
      tool_policy: 'mcp-governed',
      attached_context_sources: ['thread-history'],
      bound_at: '2026-04-18T00:00:00.000Z',
    },
    runtimeBinding: { status: 'bound', error: null },
    currentLocationLabel: 'bazzite-laptop / src / /var/home/lch/projects/bazzite-laptop',
    runtimeHealth: { mcpHealthy: true, llmHealthy: true },
    availableTools: ['system.uptime', 'providers.discover'],
    degradedStates: [],
    hasActiveThread: true,
  });

  assert.match(strip.summary, /openai/);
  assert.match(strip.summary, /gpt-4o-mini/);
  assert.match(strip.summary, /reason/);
  assert.equal(strip.status, 'Bound');
  assert.equal(strip.details.length, 4);
});

test('thread action items switch archive label correctly', () => {
  const active = getThreadActionItems({ isArchived: false });
  const archived = getThreadActionItems({ isArchived: true });

  assert.ok(active.some((item) => item.id === 'archive'));
  assert.ok(archived.some((item) => item.id === 'restore'));
  assert.equal(active[0].id, 'rename');
});
