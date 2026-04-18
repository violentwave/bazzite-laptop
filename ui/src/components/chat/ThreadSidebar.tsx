"use client";

import { Thread } from "@/types/chat";

interface ThreadSidebarProps {
  threads: Thread[];
  pinnedThreads: Thread[];
  recentThreads: Thread[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
  onTogglePin: (threadId: string) => void;
  onClose?: () => void;
}

export function ThreadSidebar({
  threads,
  pinnedThreads,
  recentThreads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onTogglePin,
  onClose,
}: ThreadSidebarProps) {
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

  const getPreview = (content: string) => {
    const firstLine = content.split("\n")[0];
    return firstLine.length > 40 ? firstLine.substring(0, 40) + "..." : firstLine || "New chat";
  };

  const ThreadItem = ({ thread, isCompact = false }: { thread: Thread; isCompact?: boolean }) => (
    <div
      className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
        activeThreadId === thread.id
          ? "bg-base-03"
          : "hover:bg-base-02"
      }`}
      onClick={() => onSelectThread(thread.id)}
      title={thread.title}
    >
      <button
        onClick={(e) => {
          e.stopPropagation();
          onTogglePin(thread.id);
        }}
        className={`shrink-0 p-1 rounded hover:bg-base-03 transition-colors ${
          thread.isPinned ? "text-accent-primary" : "text-tertiary"
        }`}
        title={thread.isPinned ? "Unpin" : "Pin"}
      >
        <PinIcon isPinned={thread.isPinned} />
      </button>
      
      <div className="flex-1 min-w-0">
        <div 
          className="text-sm font-medium truncate"
          style={{ color: "var(--text-primary)" }}
        >
          {thread.title}
        </div>
        {!isCompact && thread.messages.length > 0 && (
          <div 
            className="text-xs truncate"
            style={{ color: "var(--text-tertiary)" }}
          >
            {getPreview(
              thread.messages.length > 0 
                ? (thread.messages[thread.messages.length - 1] as { content?: string })?.content || ""
                : ""
            )}
          </div>
        )}
      </div>

      <div 
        className="text-xs shrink-0"
        style={{ color: "var(--text-tertiary)" }}
      >
        {formatDate(thread.updatedAt)}
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          if (confirm("Delete this thread?")) {
            onDeleteThread(thread.id);
          }
        }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-base-03 transition-all text-danger"
        title="Delete thread"
      >
        <TrashIcon />
      </button>
    </div>
  );

  return (
    <div
      className="h-full flex flex-col w-64 shrink-0"
      style={{
        background: "var(--base-01)",
        borderRight: "1px solid var(--base-04)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--base-04)" }}
      >
        <h3 
          className="text-sm font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          Threads
        </h3>
        <div className="flex items-center gap-1">
          <button
            onClick={onCreateThread}
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

      {/* Storage indicator */}
      <div
        className="px-4 py-2 text-xs border-b"
        style={{ 
          color: "var(--text-tertiary)",
          borderColor: "var(--base-04)",
          background: "var(--base-02)",
        }}
      >
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-warning" />
          Local only
        </span>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto py-2">
        {/* Pinned Section */}
        {pinnedThreads.length > 0 && (
          <div className="mb-4">
            <div
              className="px-4 py-2 text-xs font-medium uppercase"
              style={{ color: "var(--text-tertiary)" }}
            >
              Pinned
            </div>
            {pinnedThreads.map((thread) => (
              <ThreadItem key={thread.id} thread={thread} />
            ))}
          </div>
        )}

        {/* Recent Section */}
        {recentThreads.length > 0 && (
          <div>
            <div
              className="px-4 py-2 text-xs font-medium uppercase"
              style={{ color: "var(--text-tertiary)" }}
            >
              Recent
            </div>
            {recentThreads.map((thread) => (
              <ThreadItem key={thread.id} thread={thread} isCompact />
            ))}
          </div>
        )}

        {/* Empty State */}
        {threads.length === 0 && (
          <div
            className="flex flex-col items-center justify-center h-full px-4 text-center"
            style={{ color: "var(--text-tertiary)" }}
          >
            <div className="mb-4">
              <ChatIcon />
            </div>
            <p className="text-sm mb-2">No threads yet</p>
            <button
              onClick={onCreateThread}
              className="text-sm px-3 py-1.5 rounded-lg transition-colors"
              style={{
                background: "var(--accent-primary)",
                color: "white",
              }}
            >
              Start a new chat
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div
        className="px-4 py-2 border-t text-xs"
        style={{ 
          color: "var(--text-tertiary)",
          borderColor: "var(--base-04)",
        }}
      >
        {threads.length} thread{threads.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}

// Icons
function PinIcon({ isPinned }: { isPinned: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill={isPinned ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v4.76Z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}