import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildRuntimeMetadata,
  getProjectHydrationState,
  isProjectContextDegraded,
  modelsForProvider,
  validateWorkspaceSessionBinding,
} from './workspace-session-binding.js';

const providers = [
  { id: 'openai', name: 'OpenAI', status: 'healthy' },
  { id: 'anthropic', name: 'Anthropic', status: 'degraded' },
  { id: 'broken', name: 'Broken', status: 'blocked' },
];

const models = [
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'openai', is_available: true },
  { id: 'gpt-4.1', name: 'GPT-4.1', provider: 'openai', is_available: false },
  { id: 'claude-sonnet-4', name: 'Claude Sonnet 4', provider: 'anthropic', is_available: true },
];

const projects = [
  { id: 'bazzite-laptop', name: 'Bazzite Laptop', root_path: '/var/home/lch/projects/bazzite-laptop' },
  { id: 'opencode', name: 'OpenCode', root_path: '/var/home/lch/projects/opencode' },
];

test('validates provider/model session binding against live catalogs', () => {
  const result = validateWorkspaceSessionBinding(
    {
      mode: 'reason',
      provider: 'openai',
      model: 'gpt-4o-mini',
      project_id: 'bazzite-laptop',
    },
    providers,
    models
  );

  assert.equal(result.valid, true);
  assert.equal(result.session.provider, 'openai');
  assert.equal(result.session.model, 'gpt-4o-mini');
});

test('fails if model does not belong to selected provider', () => {
  const result = validateWorkspaceSessionBinding(
    {
      mode: 'code',
      provider: 'openai',
      model: 'claude-sonnet-4',
    },
    providers,
    models
  );

  assert.equal(result.valid, false);
  assert.match(result.error, /does not belong/);
});

test('fails if selected provider is blocked', () => {
  const result = validateWorkspaceSessionBinding(
    {
      mode: 'fast',
      provider: 'broken',
      model: 'gpt-4o-mini',
    },
    providers,
    models
  );

  assert.equal(result.valid, false);
  assert.match(result.error, /cannot be used/);
});

test('filters model list to selected provider only', () => {
  const openaiModels = modelsForProvider(models, 'openai');
  assert.deepEqual(
    openaiModels.map((item) => item.id),
    ['gpt-4o-mini']
  );
});

test('builds thread-visible runtime metadata payload', () => {
  const metadata = buildRuntimeMetadata({
    provider: 'openai',
    model: 'gpt-4o-mini',
    mode: 'reason',
    project_id: 'bazzite-laptop',
    memory_policy: 'project-bound',
    tool_policy: 'mcp-governed',
    attached_context_sources: ['thread-history', 'project-context'],
    bound_at: '2026-04-18T12:00:00.000Z',
  });

  assert.equal(metadata.provider, 'openai');
  assert.equal(metadata.model, 'gpt-4o-mini');
  assert.equal(metadata.mode, 'reason');
  assert.deepEqual(metadata.attached_context_sources, ['thread-history', 'project-context']);
});

test('getProjectHydrationState returns "selected" when no project ID', () => {
  const state = getProjectHydrationState(null, projects, false);
  assert.equal(state, 'selected');
});

test('getProjectHydrationState returns "hydrating" when binding is pending', () => {
  const state = getProjectHydrationState('bazzite-laptop', projects, true);
  assert.equal(state, 'hydrating');
});

test('getProjectHydrationState returns "hydrated" when project exists and not pending', () => {
  const state = getProjectHydrationState('bazzite-laptop', projects, false);
  assert.equal(state, 'hydrated');
});

test('getProjectHydrationState returns "unavailable" when project not found', () => {
  const state = getProjectHydrationState('nonexistent-project', projects, false);
  assert.equal(state, 'unavailable');
});

test('getProjectHydrationState handles empty project list', () => {
  const state = getProjectHydrationState('bazzite-laptop', [], false);
  assert.equal(state, 'unavailable');
});

test('isProjectContextDegraded returns true for "unavailable" state', () => {
  assert.equal(isProjectContextDegraded('unavailable'), true);
});

test('isProjectContextDegraded returns true for "invalid" state', () => {
  assert.equal(isProjectContextDegraded('invalid'), true);
});

test('isProjectContextDegraded returns false for "hydrated" state', () => {
  assert.equal(isProjectContextDegraded('hydrated'), false);
});

test('isProjectContextDegraded returns false for "selected" state', () => {
  assert.equal(isProjectContextDegraded('selected'), false);
});

test('isProjectContextDegraded returns false for "hydrating" state', () => {
  assert.equal(isProjectContextDegraded('hydrating'), false);
});
