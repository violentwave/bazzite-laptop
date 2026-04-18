import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildProjectRegisterArgs,
  extractRecentThreads,
  markThreadActive,
  summarizeRuntimeOverview,
  summarizeSecurityWidget,
} from './home-dashboard.js';

test('extracts recent non-archived threads in recency order', () => {
  const threads = extractRecentThreads(
    {
      threads: [
        {
          id: 'older',
          title: 'Older',
          messages: [],
          updatedAt: '2026-04-18T10:00:00.000Z',
          createdAt: '2026-04-18T09:00:00.000Z',
          isPinned: false,
          isArchived: false,
        },
        {
          id: 'latest',
          title: 'Latest',
          messages: [],
          updatedAt: '2026-04-18T12:00:00.000Z',
          createdAt: '2026-04-18T11:00:00.000Z',
          isPinned: true,
          isArchived: false,
          lastMode: 'reason',
        },
        {
          id: 'archived',
          title: 'Archived',
          messages: [],
          updatedAt: '2026-04-18T13:00:00.000Z',
          createdAt: '2026-04-18T11:30:00.000Z',
          isPinned: false,
          isArchived: true,
        },
      ],
    },
    5
  );

  assert.equal(threads.length, 2);
  assert.equal(threads[0].id, 'latest');
  assert.equal(threads[1].id, 'older');
  assert.equal(threads[0].mode, 'reason');
});

test('builds project register payload with trimmed tags', () => {
  const args = buildProjectRegisterArgs({
    name: '  Bazzite Laptop  ',
    path: ' /var/home/lch/projects/bazzite-laptop ',
    description: '  Console work  ',
    tags: 'p140, ui , pass-4d ,',
  });

  assert.deepEqual(args, {
    name: 'Bazzite Laptop',
    path: '/var/home/lch/projects/bazzite-laptop',
    description: 'Console work',
    tags: ['p140', 'ui', 'pass-4d'],
  });
});

test('summarizes runtime and security widgets from live data', () => {
  const runtime = summarizeRuntimeOverview(
    null,
    [
      { is_configured: true, is_healthy: true, status: 'healthy', is_local: false },
      { is_configured: true, is_healthy: false, status: 'degraded', is_local: true },
    ],
    [{ is_available: true }, { is_available: false }]
  );
  assert.equal(runtime.configured, 2);
  assert.equal(runtime.healthy, 1);
  assert.equal(runtime.degraded, 1);
  assert.equal(runtime.localProviders, 1);
  assert.equal(runtime.totalModels, 1);

  const security = summarizeSecurityWidget(
    {
      system_status: 'warning',
      critical_count: 1,
      high_count: 2,
      medium_count: 3,
      low_count: 4,
      last_scan_time: '2026-04-18T11:50:00.000Z',
    },
    [{ id: 'a' }],
    [{ id: 'f1' }, { id: 'f2' }],
    null
  );
  assert.equal(security.status, 'warning');
  assert.equal(security.critical, 1);
  assert.equal(security.alerts, 1);
  assert.equal(security.findings, 2);
});

test('marks a thread active in thread store', () => {
  const updated = markThreadActive({ version: 2, threads: [{ id: 't1' }], activeThreadId: null }, 't1');
  assert.equal(updated.activeThreadId, 't1');
});
