import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildCompactDegradedBadge,
  buildDegradedStateSummary,
  buildRuntimeIntrospectionResponse,
  classifyToolFailure,
  detectOperatorIntent,
  getOperatorActionSurface,
  summarizeToolArguments,
} from './operator-runtime.js';

test('detects truthful runtime introspection intent', () => {
  const intent = detectOperatorIntent('what provider/model are you running?');
  assert.equal(intent.type, 'introspection');
  assert.equal(intent.topic, 'provider_model');

  const actionIntent = detectOperatorIntent('run security audit now');
  assert.equal(actionIntent.type, 'tool_action');
  assert.equal(actionIntent.tool, 'agents.security_audit');
});

test('classifies blocked tool failures distinctly', () => {
  assert.equal(classifyToolFailure('Blocked by policy approval gate'), 'blocked');
  assert.equal(classifyToolFailure('Tool timeout'), 'error');
});

test('formats runtime introspection from bound session truth', () => {
  const text = buildRuntimeIntrospectionResponse({
    topic: 'runtime',
    session: {
      thread_id: 't-1',
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
    projectHydrationState: 'hydrated',
    mcpHealthy: true,
    project: { name: 'bazzite-laptop', root_path: '/var/home/lch/projects/bazzite-laptop' },
    toolPolicy: 'mcp-governed',
    availableTools: ['system.uptime'],
    degradedStates: [],
  });

  assert.match(text, /Provider: openai/);
  assert.match(text, /Model: gpt-4o-mini/);
  assert.match(text, /Mode: reason/);
  assert.match(text, /Project: bazzite-laptop/);
  assert.match(text, /Project status: hydrated/);
});

test('builds degraded state messages including project hydration states', () => {
  const degraded = buildDegradedStateSummary({
    mcpHealthy: false,
    runtimeBinding: { status: 'invalid', error: 'model mismatch' },
    projectHydrationState: 'unavailable',
    toolsAvailable: false,
  });

  assert.equal(degraded.length >= 3, true);
  assert.ok(degraded.some((item) => item === 'MCP bridge unavailable'));
  assert.ok(degraded.some((item) => item === 'Runtime binding invalid'));
  assert.ok(degraded.some((item) => item === 'Project context unavailable'));
});

test('builds compact degraded badge with appropriate condensing', () => {
  assert.equal(buildCompactDegradedBadge([]), null);
  assert.equal(buildCompactDegradedBadge(['MCP issue']), 'MCP issue');
  assert.equal(buildCompactDegradedBadge(['MCP issue', 'Project unavailable']), 'MCP issue • Project unavailable');
  assert.equal(buildCompactDegradedBadge(['Issue 1', 'Issue 2', 'Issue 3']), '3 issues');
});

test('provides operator action surface and tool argument summaries', () => {
  const actions = getOperatorActionSurface({ toolPolicy: 'approval-required' });
  assert.ok(actions.some((action) => action.id === 'tools'));
  assert.ok(actions.some((action) => action.label.includes('approval-required')));

  const summary = summarizeToolArguments({ query: 'uptime now', hours: 24, include: ['cpu', 'mem'] });
  assert.match(summary, /query=uptime now/);
  assert.match(summary, /hours=24/);
});
