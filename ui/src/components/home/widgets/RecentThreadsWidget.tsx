"use client";

import { useCallback, useEffect, useState } from "react";
import { WidgetContainer } from "./WidgetContainer";
import {
  extractRecentThreads,
  markThreadActive,
  THREADS_STORAGE_KEY,
} from "@/lib/home-dashboard";
import { useShell } from "@/components/shell/ShellContext";

type RecentThreadsWidgetProps = {
  onThreadSelect?: (threadId: string) => void;
  maxDisplay?: number;
  onRemove?: () => void;
};

export function RecentThreadsWidget({
  onThreadSelect,
  maxDisplay = 6,
  onRemove,
}: RecentThreadsWidgetProps = {}) {
  const [recentThreads, setRecentThreads] = useState<Array<{
    id: string;
    title: string;
    updatedAt: string;
    projectId: string;
    folderPath: string;
    mode: string;
    isPinned: boolean;
  }>>([]);
  const [loading, setLoading] = useState(false);
  const { setActivePanel } = useShell();

  const formatRelativeTime = useCallback((timestamp: string): string => {
    const value = new Date(timestamp).getTime();
    if (!Number.isFinite(value)) {
      return "unknown";
    }

    const deltaMs = Date.now() - value;
    const minutes = Math.floor(deltaMs / 60000);
    const hours = Math.floor(deltaMs / 3600000);
    const days = Math.floor(deltaMs / 86400000);

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return new Date(timestamp).toLocaleDateString();
  }, []);

  const refreshRecentThreads = useCallback(() => {
    setLoading(true);
    try {
      if (typeof window === "undefined") {
        setRecentThreads([]);
        setLoading(false);
        return;
      }

      const raw = localStorage.getItem(THREADS_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      setRecentThreads(extractRecentThreads(parsed, maxDisplay));
    } catch {
      setRecentThreads([]);
    } finally {
      setLoading(false);
    }
  }, [maxDisplay]);

  useEffect(() => {
    refreshRecentThreads();
    const interval = window.setInterval(refreshRecentThreads, 15000);
    const onStorage = (event: StorageEvent) => {
      if (event.key === THREADS_STORAGE_KEY) {
        refreshRecentThreads();
      }
    };

    window.addEventListener("storage", onStorage);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("storage", onStorage);
    };
  }, [refreshRecentThreads]);

  const openRecentThread = useCallback(
    (threadId: string) => {
      if (typeof window === "undefined") {
        return;
      }

      try {
        const raw = localStorage.getItem(THREADS_STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : null;
        const updated = markThreadActive(parsed, threadId);
        localStorage.setItem(THREADS_STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Ignore local persistence errors and still switch panels.
      }

      setActivePanel("chat");
      onThreadSelect?.(threadId);
    },
    [setActivePanel, onThreadSelect]
  );

  if (loading) {
    return (
      <WidgetContainer
        title="Recent Threads"
        subtitle="Continue recent local chat work"
        onRemove={onRemove}
      >
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </WidgetContainer>
    );
  }

  return (
    <WidgetContainer
      title="Recent Threads"
      subtitle="Continue recent local chat work"
      onRemove={onRemove}
    >
      {recentThreads.length === 0 ? (
        <div className="text-sm px-3 py-2 rounded-lg border border-base-4 bg-base-1 text-tertiary">
          No recent threads yet. Open Chat Workspace to start one.
        </div>
      ) : (
        <div className="space-y-2">
          {recentThreads.map((thread) => (
            <button
              key={thread.id}
              onClick={() => openRecentThread(thread.id)}
              className="w-full text-left rounded-lg px-3 py-2 transition-colors hover:bg-base-1"
              style={{
                border: "1px solid var(--base-4)",
                background: thread.isPinned ? "var(--accent-primary)/10" : "var(--base-2)",
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm truncate text-primary" title={thread.title}>
                  {thread.title}
                </span>
                <span className="text-xs shrink-0 text-tertiary">
                  {formatRelativeTime(thread.updatedAt)}
                </span>
              </div>
              <div className="mt-1 text-xs text-secondary">
                {(thread.projectId ? thread.projectId : "Unassigned")}{thread.folderPath && ` / ${thread.folderPath}`} · {thread.mode}
                {thread.isPinned ? " · pinned" : ""}
              </div>
            </button>
          ))}
        </div>
      )}
    </WidgetContainer>
  );
}
