"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Thread } from "@/types/chat";
import { getThreadActionItems } from "@/lib/console-simplify";

interface ThreadSidebarProps {
  threads: Thread[];
  pinnedThreads: Thread[];
  recentThreads: Thread[];
  groupedThreadsByProject: Array<{ projectId: string; projectName: string; threads: Thread[] }>;
  archivedThreads: Thread[];
  projects: Array<{ project_id: string; name?: string; root_path?: string }>;
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: (options?: {
    title?: string;
    projectId?: string;
    folderPath?: string;
    inheritProjectContext?: boolean;
  }) => void;
  onDeleteThread: (threadId: string) => void;
  onTogglePin: (threadId: string) => void;
  onRenameThread: (threadId: string, title: string) => void;
  onMoveThread: (threadId: string, projectId: string, folderPath?: string) => void;
  onArchiveThread: (threadId: string) => void;
  onUnarchiveThread: (threadId: string) => void;
  onClose?: () => void;
  isBulkSelectMode?: boolean;
  selectedThreadIds?: string[];
  onToggleBulkSelectMode?: () => void;
  onToggleThreadSelection?: (threadId: string) => void;
  onClearThreadSelection?: () => void;
  onMergeThreads?: (threadIdsToMerge: string[], newTitle: string, mergePolicy: { projectId?: string; folderPath?: string; archiveOriginals: boolean }) => Promise<string | null>;
  onMoveSelectedThreadsToProject?: (projectId: string, folderPath?: string) => void;
  onArchiveSelectedThreads?: () => void;
}

type ThreadAction = "rename" | "move" | "archive" | "restore" | "delete";

export function ThreadSidebar({
  threads,
  pinnedThreads,
  recentThreads,
  groupedThreadsByProject,
  archivedThreads,
  projects,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onTogglePin,
  onRenameThread,
  onMoveThread,
  onArchiveThread,
  onUnarchiveThread,
  onClose,
  isBulkSelectMode,
  selectedThreadIds,
  onToggleBulkSelectMode,
  onToggleThreadSelection,
  onClearThreadSelection,
  onMergeThreads,
  onMoveSelectedThreadsToProject,
  onArchiveSelectedThreads,
}: ThreadSidebarProps) {
  const [activeMenuThreadId, setActiveMenuThreadId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);

  const [newThreadTitle, setNewThreadTitle] = useState("");
  const [newThreadProjectId, setNewThreadProjectId] = useState("");
  const [newThreadFolderPath, setNewThreadFolderPath] = useState("");
  const [inheritProjectContext, setInheritProjectContext] = useState(true);

  const [renameDraft, setRenameDraft] = useState("");
  const [moveProjectId, setMoveProjectId] = useState("");
  const [moveFolderPath, setMoveFolderPath] = useState("");

  const [mergeTitle, setMergeTitle] = useState("");
  const [mergeProjectId, setMergeProjectId] = useState("");
  const [mergeFolderPath, setMergeFolderPath] = useState("");
  const [mergeArchiveOriginals, setMergeArchiveOriginals] = useState(true);

  const menuRef = useRef<HTMLDivElement | null>(null);

  const projectNameById = useMemo(
    () => new Map(projects.map((project) => [project.project_id, project.name || project.project_id])),
    [projects]
  );

  useEffect(() => {
    if (!activeMenuThreadId) return;

    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setActiveMenuThreadId(null);
      }
    };

    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [activeMenuThreadId]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const runThreadAction = (thread: Thread, action: ThreadAction) => {
    setActiveMenuThreadId(null);

    if (action === "rename") {
      setSelectedThread(thread);
      setRenameDraft(thread.title);
      setShowRenameModal(true);
      return;
    }

    if (action === "move") {
      setSelectedThread(thread);
      setMoveProjectId(thread.projectId || "");
      setMoveFolderPath(thread.folderPath || "");
      setShowMoveModal(true);
      return;
    }

    if (action === "archive") {
      onArchiveThread(thread.id);
      return;
    }

    if (action === "restore") {
      onUnarchiveThread(thread.id);
      return;
    }

    if (action === "delete") {
      setSelectedThread(thread);
      setShowDeleteModal(true);
    }
  };

  const ThreadItem = ({ thread }: { thread: Thread }) => {
    const isActive = activeThreadId === thread.id;
    const isSelected = selectedThreadIds?.includes(thread.id) || false;
    const projectLabel = thread.projectId
      ? projectNameById.get(thread.projectId) || thread.projectId
      : "Unassigned";

    return (
      <div
        className="group px-3 py-2 rounded-lg transition-colors relative"
        style={{ background: isActive || isSelected ? "var(--base-03)" : "transparent" }}
      >
        <div className="flex items-center gap-2">
          {isBulkSelectMode && onToggleThreadSelection && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => onToggleThreadSelection(thread.id)}
              className="mr-1"
            />
          )}
          {!isBulkSelectMode && (
            <button
              onClick={() => onTogglePin(thread.id)}
              className={`shrink-0 p-1 rounded transition-colors ${thread.isPinned ? "text-accent-primary" : "text-tertiary"}`}
              title={thread.isPinned ? "Unpin" : "Pin"}
            >
              <PinIcon isPinned={thread.isPinned} />
            </button>
          )}

          <button onClick={() => onSelectThread(thread.id)} className="flex-1 min-w-0 text-left" title={thread.title} disabled={isBulkSelectMode}>
            <div className="text-sm font-medium truncate flex items-center gap-1" style={{ color: "var(--text-primary)" }}>
              {thread.title}
              {thread.isMerged && (
                <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--base-04)', color: 'var(--text-secondary)' }}>Merged</span>
              )}
            </div>
            {(thread.projectId || thread.folderPath) && (
              <div className="text-[11px] truncate" style={{ color: "var(--text-tertiary)" }}>
                {projectLabel}
                {thread.folderPath ? ` / ${thread.folderPath}` : ""}
              </div>
            )}
          </button>

          <span className="text-xs shrink-0" style={{ color: "var(--text-tertiary)" }}>
            {formatDate(thread.updatedAt)}
          </span>

          {!isBulkSelectMode && (
            <div className="relative">
              <button
                onClick={() => setActiveMenuThreadId((prev) => (prev === thread.id ? null : thread.id))}
                className="p-1 rounded opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                style={{
                  color: "var(--text-secondary)",
                  background: activeMenuThreadId === thread.id ? "var(--base-02)" : "transparent",
                }}
                title="Thread actions"
              >
                <KebabIcon />
              </button>

              {activeMenuThreadId === thread.id && (
                <div
                  ref={menuRef}
                  className="absolute right-0 top-8 z-30 min-w-[132px] rounded-lg py-1"
                  style={{
                    background: "var(--base-01)",
                    border: "1px solid var(--base-04)",
                    boxShadow: "var(--shadow-lg)",
                  }}
                >
                  {getThreadActionItems(thread).map((action) => (
                    <button
                      key={action.id}
                      onClick={() => runThreadAction(thread, action.id)}
                      className="w-full text-left px-3 py-1.5 text-xs transition-colors hover:bg-base-02"
                      style={{
                        color:
                          action.id === "delete"
                            ? "var(--danger)"
                            : action.id === "archive"
                              ? "var(--warning)"
                              : "var(--text-secondary)",
                      }}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div
      className="h-full flex flex-col w-80 shrink-0"
      style={{ background: "var(--base-01)", borderRight: "1px solid var(--base-04)" }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "var(--base-04)" }}>
        <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Threads
        </h3>
        <div className="flex items-center gap-1">
          {onToggleBulkSelectMode && (
            <button
              onClick={onToggleBulkSelectMode}
              className={`text-[10px] px-1.5 py-1 rounded transition-colors mr-1 ${isBulkSelectMode ? 'bg-accent-primary text-white' : 'hover:bg-base-03 text-secondary'}`}
              style={!isBulkSelectMode ? { color: "var(--text-secondary)", border: "1px solid var(--base-04)" } : undefined}
              title={isBulkSelectMode ? "Cancel bulk select" : "Bulk select"}
            >
              {isBulkSelectMode ? "Cancel" : "Select"}
            </button>
          )}
          <button
            onClick={() => setShowCreateModal(true)}
            className="p-1.5 rounded hover:bg-base-03 transition-colors"
            style={{ color: "var(--accent-primary)" }}
            title="New thread"
          >
            <PlusIcon />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-base-03 transition-colors"
              style={{ color: "var(--text-secondary)" }}
              title="Close sidebar"
            >
              <CloseIcon />
            </button>
          )}
        </div>
      </div>

      <div
        className="px-4 py-2 text-xs border-b"
        style={{ color: "var(--text-tertiary)", borderColor: "var(--base-04)", background: "var(--base-02)" }}
      >
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-warning" />
          Local only
        </span>
      </div>

      <div className="flex-1 overflow-y-auto py-2 space-y-4">
        {pinnedThreads.length > 0 && (
          <section>
            <div className="px-4 py-1 text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>
              Pinned
            </div>
            {pinnedThreads.map((thread) => (
              <ThreadItem key={thread.id} thread={thread} />
            ))}
          </section>
        )}

        {recentThreads.length > 0 && (
          <section>
            <div className="px-4 py-1 text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>
              Recent
            </div>
            {recentThreads.map((thread) => (
              <ThreadItem key={thread.id} thread={thread} />
            ))}
          </section>
        )}

        {groupedThreadsByProject.length > 0 && (
          <section>
            <div className="px-4 py-1 text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>
              By Project
            </div>
            {groupedThreadsByProject.map((group) => (
              <div key={group.projectId || "unassigned"} className="mb-3">
                <div className="px-4 py-1 text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>
                  {group.projectName}
                </div>
                {group.threads.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} />
                ))}
              </div>
            ))}
          </section>
        )}

        {archivedThreads.length > 0 && (
          <section>
            <div className="px-4 py-1 text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>
              Archived
            </div>
            <div className="px-4 pb-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              Hidden from active lists. Use thread actions to Restore to bring a thread back.
            </div>
            {archivedThreads.map((thread) => (
              <ThreadItem key={thread.id} thread={thread} />
            ))}
          </section>
        )}

        {threads.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full px-4 text-center" style={{ color: "var(--text-tertiary)" }}>
            <div className="mb-4">
              <ChatIcon />
            </div>
            <p className="text-sm mb-2">No threads yet</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="text-sm px-3 py-1.5 rounded-lg transition-colors"
              style={{ background: "var(--accent-primary)", color: "white" }}
            >
              Start a new chat
            </button>
          </div>
        )}
      </div>

      {isBulkSelectMode ? (
        <div className="px-3 py-3 border-t flex flex-col gap-2" style={{ borderColor: "var(--base-04)", background: "var(--base-02)" }}>
          <div className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
            {selectedThreadIds?.length || 0} selected
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setShowMergeModal(true)}
              disabled={(selectedThreadIds?.length || 0) < 2}
              className="text-xs px-2 py-1 rounded disabled:opacity-50"
              style={{ background: "var(--accent-primary)", color: "white" }}
            >
              Merge
            </button>
            <button
              onClick={() => {
                setMoveProjectId("");
                setMoveFolderPath("");
                setShowMoveModal(true);
              }}
              disabled={(selectedThreadIds?.length || 0) === 0}
              className="text-xs px-2 py-1 rounded disabled:opacity-50"
              style={{ background: "var(--base-03)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
            >
              Move
            </button>
            <button
              onClick={() => {
                onArchiveSelectedThreads?.();
                onToggleBulkSelectMode?.();
              }}
              disabled={(selectedThreadIds?.length || 0) === 0}
              className="text-xs px-2 py-1 rounded disabled:opacity-50"
              style={{ background: "var(--base-03)", color: "var(--warning)", border: "1px solid var(--base-04)" }}
            >
              Archive to Archived
            </button>
          </div>
          <div className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
            Archived threads move to the Archived section and can be restored from thread actions.
          </div>
        </div>
      ) : (
        <div className="px-4 py-2 border-t text-xs" style={{ color: "var(--text-tertiary)", borderColor: "var(--base-04)" }}>
          {threads.length} thread{threads.length !== 1 ? "s" : ""}
        </div>
      )}

      {showCreateModal && (
        <ModalFrame title="Create Thread" onClose={() => setShowCreateModal(false)}>
          <input
            value={newThreadTitle}
            onChange={(event) => setNewThreadTitle(event.target.value)}
            placeholder="Thread title (optional)"
            className="w-full text-xs px-2 py-1 rounded"
            style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
          />
          <select
            value={newThreadProjectId}
            onChange={(event) => setNewThreadProjectId(event.target.value)}
            className="w-full text-xs px-2 py-1 rounded mt-2"
            style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
          >
            <option value="">Unassigned</option>
            {projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.name || project.project_id}
              </option>
            ))}
          </select>
          <input
            value={newThreadFolderPath}
            onChange={(event) => setNewThreadFolderPath(event.target.value)}
            placeholder="Folder path (optional)"
            className="w-full text-xs px-2 py-1 rounded mt-2"
            style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
          />
          <label className="flex items-center gap-2 text-xs mt-2" style={{ color: "var(--text-secondary)" }}>
            <input
              type="checkbox"
              checked={inheritProjectContext}
              onChange={(event) => setInheritProjectContext(event.target.checked)}
            />
            Inherit project context
          </label>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => {
                onCreateThread({
                  title: newThreadTitle || undefined,
                  projectId: newThreadProjectId,
                  folderPath: newThreadFolderPath || undefined,
                  inheritProjectContext,
                });
                setNewThreadTitle("");
                setNewThreadProjectId("");
                setNewThreadFolderPath("");
                setShowCreateModal(false);
              }}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--accent-primary)", color: "white" }}
            >
              Create
            </button>
            <button
              onClick={() => setShowCreateModal(false)}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--base-01)", color: "var(--text-secondary)", border: "1px solid var(--base-04)" }}
            >
              Cancel
            </button>
          </div>
        </ModalFrame>
      )}

      {showRenameModal && selectedThread && (
        <ModalFrame title="Rename Thread" onClose={() => setShowRenameModal(false)}>
          <input
            value={renameDraft}
            onChange={(event) => setRenameDraft(event.target.value)}
            className="w-full text-xs px-2 py-1 rounded"
            style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => {
                const title = renameDraft.trim();
                if (title) {
                  onRenameThread(selectedThread.id, title);
                }
                setShowRenameModal(false);
              }}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--accent-primary)", color: "white" }}
            >
              Save
            </button>
            <button
              onClick={() => setShowRenameModal(false)}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--base-01)", color: "var(--text-secondary)", border: "1px solid var(--base-04)" }}
            >
              Cancel
            </button>
          </div>
        </ModalFrame>
      )}

      {showMoveModal && (selectedThread || isBulkSelectMode) && (
        <ModalFrame title="Move Thread(s)" onClose={() => setShowMoveModal(false)}>
          <select
            value={moveProjectId}
            onChange={(event) => setMoveProjectId(event.target.value)}
            className="w-full text-xs px-2 py-1 rounded"
            style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
          >
            <option value="">Unassigned</option>
            {projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.name || project.project_id}
              </option>
            ))}
          </select>
          <input
            value={moveFolderPath}
            onChange={(event) => setMoveFolderPath(event.target.value)}
            placeholder="Folder path (optional)"
            className="w-full text-xs px-2 py-1 rounded mt-2"
            style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => {
                if (isBulkSelectMode && onMoveSelectedThreadsToProject) {
                  onMoveSelectedThreadsToProject(moveProjectId, moveFolderPath.trim());
                  onToggleBulkSelectMode?.();
                } else if (selectedThread) {
                  onMoveThread(selectedThread.id, moveProjectId, moveFolderPath.trim());
                }
                setShowMoveModal(false);
              }}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--accent-primary)", color: "white" }}
            >
              Save move
            </button>
            <button
              onClick={() => setShowMoveModal(false)}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--base-01)", color: "var(--text-secondary)", border: "1px solid var(--base-04)" }}
            >
              Cancel
            </button>
          </div>
        </ModalFrame>
      )}

      {showDeleteModal && selectedThread && (
        <ModalFrame title="Delete Thread" onClose={() => setShowDeleteModal(false)}>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Delete local thread "{selectedThread.title}"?
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => {
                onDeleteThread(selectedThread.id);
                setShowDeleteModal(false);
              }}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--danger)", color: "white" }}
            >
              Delete
            </button>
            <button
              onClick={() => setShowDeleteModal(false)}
              className="text-xs px-2 py-1 rounded"
              style={{ background: "var(--base-01)", color: "var(--text-secondary)", border: "1px solid var(--base-04)" }}
            >
              Cancel
            </button>
          </div>
        </ModalFrame>
      )}

      {showMergeModal && (
        <ModalFrame title="Merge Threads" onClose={() => setShowMergeModal(false)}>
          <div className="flex flex-col gap-2">
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
              Merge {selectedThreadIds?.length || 0} threads into a single chronological thread.
            </p>
            <input
              value={mergeTitle}
              onChange={(event) => setMergeTitle(event.target.value)}
              placeholder="Merged thread title (optional)"
              className="w-full text-xs px-2 py-1 rounded mt-2"
              style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
            />
            <select
              value={mergeProjectId}
              onChange={(event) => setMergeProjectId(event.target.value)}
              className="w-full text-xs px-2 py-1 rounded mt-2"
              style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
            >
              <option value="">Unassigned</option>
              {projects.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name || project.project_id}
                </option>
              ))}
            </select>
            <input
              value={mergeFolderPath}
              onChange={(event) => setMergeFolderPath(event.target.value)}
              placeholder="Folder path (optional)"
              className="w-full text-xs px-2 py-1 rounded mt-2"
              style={{ background: "var(--base-01)", color: "var(--text-primary)", border: "1px solid var(--base-04)" }}
            />
            <label className="flex items-center gap-2 text-xs mt-2" style={{ color: "var(--text-secondary)" }}>
              <input
                type="checkbox"
                checked={mergeArchiveOriginals}
                onChange={(event) => setMergeArchiveOriginals(event.target.checked)}
              />
              Archive original threads to Archived
            </label>
            <div className="flex gap-2 mt-3">
              <button
                onClick={async () => {
                  if (onMergeThreads && selectedThreadIds) {
                    await onMergeThreads(selectedThreadIds, mergeTitle, {
                      projectId: mergeProjectId,
                      folderPath: mergeFolderPath,
                      archiveOriginals: mergeArchiveOriginals,
                    });
                    setShowMergeModal(false);
                    onToggleBulkSelectMode?.();
                  }
                }}
                className="text-xs px-2 py-1 rounded"
                style={{ background: "var(--accent-primary)", color: "white" }}
              >
                Merge Threads
              </button>
              <button
                onClick={() => setShowMergeModal(false)}
                className="text-xs px-2 py-1 rounded"
                style={{ background: "var(--base-01)", color: "var(--text-secondary)", border: "1px solid var(--base-04)" }}
              >
                Cancel
              </button>
            </div>
          </div>
        </ModalFrame>
      )}
    </div>
  );
}

function ModalFrame({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0, 0, 0, 0.45)" }}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="w-full max-w-md rounded-xl p-4"
        style={{
          background: "var(--base-02)",
          border: "1px solid var(--base-04)",
          boxShadow: "var(--shadow-xl)",
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h4>
          <button
            onClick={onClose}
            className="px-2 py-1 rounded text-xs"
            style={{
              background: "var(--base-01)",
              color: "var(--text-secondary)",
              border: "1px solid var(--base-04)",
            }}
          >
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function PinIcon({ isPinned }: { isPinned: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill={isPinned ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
      <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v4.76Z" />
    </svg>
  );
}

function KebabIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="5" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="12" cy="19" r="1" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
