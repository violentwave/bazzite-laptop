import { Thread } from '@/types/chat';
type ProjectRef = { project_id: string; name?: string; root_path?: string };

export function normalizeThread(raw: Partial<Thread>): Thread;

export function updateThreadInStore(
  store: { version: number; threads: Thread[]; activeThreadId: string | null },
  threadId: string,
  updater: (thread: Thread) => Thread
): { version: number; threads: Thread[]; activeThreadId: string | null };

export function renameThreadInStore(
  store: { version: number; threads: Thread[]; activeThreadId: string | null },
  threadId: string,
  title: string
): { store: { version: number; threads: Thread[]; activeThreadId: string | null }; changed: boolean };

export function moveThreadToProjectInStore(
  store: { version: number; threads: Thread[]; activeThreadId: string | null },
  threadId: string,
  projectId: string,
  folderPath?: string
): { store: { version: number; threads: Thread[]; activeThreadId: string | null }; changed: boolean };

export function setThreadArchivedState(
  store: { version: number; threads: Thread[]; activeThreadId: string | null },
  threadId: string,
  isArchived: boolean
): { store: { version: number; threads: Thread[]; activeThreadId: string | null }; changed: boolean };

export function mergeThreadsInStore(
  store: { version: number; threads: Thread[]; activeThreadId: string | null },
  threadIdsToMerge: string[],
  newTitle: string,
  mergePolicy: { projectId?: string; folderPath?: string; archiveOriginals: boolean }
): { 
  store: { version: number; threads: Thread[]; activeThreadId: string | null }; 
  newThread: Thread | null; 
  changed: boolean; 
  error: string | null;
};

export function groupThreads(
  threads: Thread[],
  projects?: ProjectRef[]
): {
  pinned: Thread[];
  recent: Thread[];
  byProject: Array<{ projectId: string; projectName: string; threads: Thread[] }>;
  archived: Thread[];
};

export function buildThreadLocationLabel(thread: Partial<Thread>, projects?: ProjectRef[]): string;
