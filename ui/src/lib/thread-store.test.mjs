import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildThreadLocationLabel,
  groupThreads,
  moveThreadToProjectInStore,
  normalizeThread,
  renameThreadInStore,
  mergeThreadsInStore,
} from './thread-store.js';

const projects = [
  {
    project_id: 'bazzite-laptop',
    name: 'Bazzite Laptop',
    root_path: '/var/home/lch/projects/bazzite-laptop',
  },
  {
    project_id: 'security',
    name: 'Security',
    root_path: '/var/home/lch/projects/security',
  },
];

function makeStore() {
  return {
    version: 1,
    activeThreadId: 't-1',
    threads: [
      normalizeThread({
        id: 't-1',
        title: 'Initial thread',
        messages: [],
        isPinned: true,
        projectId: 'bazzite-laptop',
        provider: 'openai',
        model: 'gpt-4o-mini',
        mode: 'reason',
        createdAt: '2026-04-18T10:00:00.000Z',
        updatedAt: '2026-04-18T11:00:00.000Z',
      }),
      normalizeThread({
        id: 't-2',
        title: 'Follow-up',
        messages: [],
        isPinned: false,
        projectId: 'security',
        createdAt: '2026-04-18T09:00:00.000Z',
        updatedAt: '2026-04-18T12:00:00.000Z',
      }),
      normalizeThread({
        id: 't-3',
        title: 'Scratchpad',
        messages: [],
        isPinned: false,
        projectId: '',
        createdAt: '2026-04-18T08:00:00.000Z',
        updatedAt: '2026-04-18T08:00:00.000Z',
      }),
    ],
  };
}

test('rename thread updates title and keeps metadata persisted', () => {
  const { store } = renameThreadInStore(makeStore(), 't-1', 'Renamed Operator Thread');
  const renamed = store.threads.find((thread) => thread.id === 't-1');
  assert.equal(renamed.title, 'Renamed Operator Thread');
  assert.ok(renamed.updatedAt);
  assert.equal(renamed.created_at, '2026-04-18T10:00:00.000Z');
  assert.equal(renamed.lastProvider, 'openai');
  assert.equal(renamed.lastModel, 'gpt-4o-mini');
  assert.equal(renamed.lastMode, 'reason');
});

test('move thread to project stores project and folder path', () => {
  const { store } = moveThreadToProjectInStore(makeStore(), 't-3', 'bazzite-laptop', 'ops/incidents');
  const moved = store.threads.find((thread) => thread.id === 't-3');
  assert.equal(moved.projectId, 'bazzite-laptop');
  assert.equal(moved.folderPath, 'ops/incidents');
});

test('groups threads by pinned/recent/project', () => {
  const grouped = groupThreads(makeStore().threads, projects);
  assert.deepEqual(grouped.pinned.map((thread) => thread.id), ['t-1']);
  assert.deepEqual(grouped.recent.map((thread) => thread.id), ['t-2', 't-3']);
  assert.equal(grouped.byProject[0].projectId, 'bazzite-laptop');
  assert.equal(grouped.byProject[1].projectId, 'security');
  assert.equal(grouped.byProject[2].projectId, '');
});

test('builds current project/location label for chat header display', () => {
  const label = buildThreadLocationLabel(
    {
      id: 't-1',
      title: 'Thread',
      messages: [],
      projectId: 'bazzite-laptop',
      folderPath: 'ops/incidents',
      createdAt: '2026-04-18T10:00:00.000Z',
      updatedAt: '2026-04-18T11:00:00.000Z',
      isPinned: false,
    },
    projects
  );
  assert.equal(label, 'Bazzite Laptop / ops/incidents / /var/home/lch/projects/bazzite-laptop');
});

test('mergeThreadsInStore merges messages chronologically and archives originals', () => {
  const store = makeStore();
  // Add some messages
  store.threads[0].messages = [
    { id: 'm1', content: 'hello', timestamp: '2026-04-18T10:05:00.000Z' },
    { id: 'm3', content: 'how are you', timestamp: '2026-04-18T10:15:00.000Z' }
  ];
  store.threads[1].messages = [
    { id: 'm2', content: 'world', timestamp: '2026-04-18T10:10:00.000Z' }
  ];

  const result = mergeThreadsInStore(store, ['t-1', 't-2'], 'Merged test', { projectId: 'security', folderPath: 'merged', archiveOriginals: true });
  
  assert.ok(result.changed);
  assert.equal(result.newThread.title, 'Merged test');
  assert.equal(result.newThread.projectId, 'security');
  assert.equal(result.newThread.folderPath, 'merged');
  assert.equal(result.newThread.isMerged, true);
  
  // Messages should be chronologically ordered: m1, m2, m3
  assert.equal(result.newThread.messages.length, 3);
  assert.equal(result.newThread.messages[0].id, 'm1');
  assert.equal(result.newThread.messages[1].id, 'm2');
  assert.equal(result.newThread.messages[2].id, 'm3');
  
  // Original threads should be archived
  const originalT1 = result.store.threads.find(t => t.id === 't-1');
  const originalT2 = result.store.threads.find(t => t.id === 't-2');
  assert.equal(originalT1.isArchived, true);
  assert.equal(originalT2.isArchived, true);
  assert.equal(originalT1.isPinned, false); // Pinned status removed on archive
});

test('mergeThreadsInStore preserves originals when archiveOriginals is false', () => {
  const store = makeStore();
  const result = mergeThreadsInStore(store, ['t-1', 't-2'], 'Merged without archive', { projectId: 'security', folderPath: '', archiveOriginals: false });
  
  // Original threads should be removed from store if not archived (they are consumed into the merged thread)
  const originalT1 = result.store.threads.find(t => t.id === 't-1');
  const originalT2 = result.store.threads.find(t => t.id === 't-2');
  assert.ok(!originalT1);
  assert.ok(!originalT2);
});

test('mergeThreadsInStore requires at least two threads', () => {
  const store = makeStore();
  const result = mergeThreadsInStore(store, ['t-1'], 'Invalid merge', { projectId: 'security', folderPath: '', archiveOriginals: false });
  
  assert.equal(result.changed, false);
  assert.ok(result.error);
});
