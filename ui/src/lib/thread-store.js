import { v4 as uuidv4 } from 'uuid';
/**
 * Thread storage helpers for local-first persistence.
 */

function nowIso() {
  return new Date().toISOString();
}

export function normalizeThread(raw) {
  const created = raw?.createdAt || raw?.created_at || nowIso();
  const updated = raw?.updatedAt || raw?.updated_at || created;
  const projectId = raw?.projectId || raw?.project_id || '';

  return {
    ...raw,
    title: typeof raw?.title === 'string' && raw.title.trim() ? raw.title.trim() : 'Untitled thread',
    messages: Array.isArray(raw?.messages) ? raw.messages : [],
    projectId,
    folderPath: typeof raw?.folderPath === 'string' ? raw.folderPath : '',
    createdAt: created,
    updatedAt: updated,
    created_at: created,
    updated_at: updated,
    isPinned: Boolean(raw?.isPinned),
    isArchived: Boolean(raw?.isArchived),
    provider: raw?.provider || '',
    model: raw?.model || '',
    mode: raw?.mode || 'fast',
    lastProvider: raw?.lastProvider || raw?.provider || '',
    lastModel: raw?.lastModel || raw?.model || '',
    lastMode: raw?.lastMode || raw?.mode || 'fast',
  };
}

export function updateThreadInStore(store, threadId, updater) {
  const updatedThreads = (store.threads || []).map((thread) => {
    if (thread.id !== threadId) {
      return thread;
    }
    const next = updater(normalizeThread(thread));
    const updatedAt = nowIso();
    return normalizeThread({
      ...next,
      updatedAt,
      updated_at: updatedAt,
    });
  });

  return {
    ...store,
    threads: updatedThreads,
  };
}

export function renameThreadInStore(store, threadId, title) {
  const cleanTitle = typeof title === 'string' ? title.trim() : '';
  if (!cleanTitle) {
    return { store, changed: false };
  }

  return {
    store: updateThreadInStore(store, threadId, (thread) => ({ ...thread, title: cleanTitle })),
    changed: true,
  };
}

export function moveThreadToProjectInStore(store, threadId, projectId, folderPath = '') {
  return {
    store: updateThreadInStore(store, threadId, (thread) => ({
      ...thread,
      projectId: projectId || '',
      folderPath: folderPath || '',
    })),
    changed: true,
  };
}

export function setThreadArchivedState(store, threadId, isArchived) {
  return {
    store: updateThreadInStore(store, threadId, (thread) => ({
      ...thread,
      isArchived,
      isPinned: isArchived ? false : thread.isPinned,
    })),
    changed: true,
  };
}

export function mergeThreadsInStore(
  store,
  threadIdsToMerge,
  newTitle,
  mergePolicy // { projectId?: string; folderPath?: string; archiveOriginals: boolean }
) {
  const threadsToMerge = threadIdsToMerge
    .map((id) => store.threads.find((t) => t.id === id))
    .filter(Boolean)
    .map(normalizeThread);

  if (threadsToMerge.length < 2) {
    return { store, newThread: null, changed: false, error: 'Select at least two threads to merge.' };
  }

  // Collect and sort messages
  const allMessages = threadsToMerge.flatMap((thread) =>
    thread.messages.map((msg) => ({
      ...msg,
      sourceThreadIds: [...(msg.sourceThreadIds || []), thread.id],
    }))
  );

  allMessages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  // Determine merged thread metadata
  const firstThread = threadsToMerge[0];
  const mergedProjectId = mergePolicy.projectId || firstThread.projectId || '';
  const mergedFolderPath = mergePolicy.folderPath || firstThread.folderPath || '';

  const newMergedThread = normalizeThread({
    id: uuidv4(),
    title: newTitle || `Merged Thread ${new Date().toLocaleDateString()}`,
    messages: allMessages, // Keep as unknown[] for now, will deserialize on load
    projectId: mergedProjectId,
    folderPath: mergedFolderPath,
    createdAt: nowIso(),
    updatedAt: nowIso(),
    isPinned: false, // Merged threads are not pinned by default
    isArchived: false, // Merged threads are not archived by default
    isMerged: true,
    // Inherit runtime metadata from the most recent thread for a sensible default
    workspaceSession: threadsToMerge[threadsToMerge.length - 1].workspaceSession,
    runtimeMetadata: threadsToMerge[threadsToMerge.length - 1].runtimeMetadata,
    provider: threadsToMerge[threadsToMerge.length - 1].provider,
    model: threadsToMerge[threadsToMerge.length - 1].model,
    mode: threadsToMerge[threadsToMerge.length - 1].mode,
    lastProvider: threadsToMerge[threadsToMerge.length - 1].lastProvider,
    lastModel: threadsToMerge[threadsToMerge.length - 1].lastModel,
    lastMode: threadsToMerge[threadsToMerge.length - 1].lastMode,
  });

  let updatedThreads = [newMergedThread, ...store.threads];

  // Handle original threads: archive or remove
  if (mergePolicy.archiveOriginals) {
    for (const threadId of threadIdsToMerge) {
      updatedThreads = setThreadArchivedState({ threads: updatedThreads }, threadId, true).store.threads;
    }
  } else {
    // If not archiving, filter out the original threads from the list
    updatedThreads = updatedThreads.filter((thread) => !threadIdsToMerge.includes(thread.id));
  }

  const updatedStore = {
    ...store,
    threads: updatedThreads,
    activeThreadId: newMergedThread.id,
  };

  return { store: updatedStore, newThread: newMergedThread, changed: true, error: null };
}

export function groupThreads(threads, projects = []) {
  const normalized = (threads || []).map(normalizeThread);
  const active = normalized.filter((thread) => !thread.isArchived);
  const byUpdated = [...active].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  );

  const pinned = byUpdated.filter((thread) => thread.isPinned);
  const pinnedIds = new Set(pinned.map(t => t.id));

  // Recent threads are non-pinned, non-archived, most recent
  const recentCandidates = byUpdated.filter((thread) => !pinnedIds.has(thread.id));
  const recent = recentCandidates.slice(0, 12); // Top 12 recent
  const recentIds = new Set(recent.map((thread) => thread.id));
  const highlightedIds = new Set([...pinnedIds, ...recentIds]);

  const nameById = new Map(
    (projects || []).map((project) => [project.project_id, project.name || project.project_id])
  );

  const buckets = new Map();
  // By Project shows remaining active threads not already highlighted
  for (const thread of active) {
    if (highlightedIds.has(thread.id)) {
      continue;
    }
    const projectId = thread.projectId || ''; // Ensure projectId is always a string
    const bucketKey = projectId || '__unassigned__';
    if (!buckets.has(bucketKey)) {
      buckets.set(bucketKey, {
        projectId: projectId, // Use the actual projectId (or empty string for unassigned)
        projectName: projectId ? nameById.get(projectId) || projectId : 'Unassigned',
        threads: [],
      });
    }
    buckets.get(bucketKey).threads.push(thread);
  }

  // Sort threads within each project bucket by update date
  for (const bucket of buckets.values()) {
    bucket.threads.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }

  const byProject = [...buckets.values()].sort((a, b) => {
    // Sort unassigned last, then by project name
    if (a.projectId === '' && b.projectId !== '') return 1;
    if (a.projectId !== '' && b.projectId === '') return -1;
    return a.projectName.localeCompare(b.projectName);
  });

  return {
    pinned,
    recent,
    byProject,
    archived: normalized.filter((thread) => thread.isArchived),
  };
}

export function buildThreadLocationLabel(thread, projects = []) {
  const normalized = normalizeThread(thread || {});
  const project = (projects || []).find((item) => item.project_id === normalized.projectId);
  const projectName = project?.name || normalized.projectId || 'No project';
  const root = project?.root_path || '';
  const folder = normalized.folderPath || '';

  const parts = [projectName];
  if (folder) {
    parts.push(folder);
  }
  if (root) {
    parts.push(root);
  }
  return parts.join(' / ');
}
