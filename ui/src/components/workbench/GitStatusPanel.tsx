"use client";

import { WorkbenchGitStatus } from "@/types/agent-workbench";

interface GitStatusPanelProps {
  gitStatus: WorkbenchGitStatus | null;
  isLoading: boolean;
  selectedProjectId: string | null;
  error: string | null;
  onRefresh: () => Promise<void>;
}

export function GitStatusPanel({
  gitStatus,
  isLoading,
  selectedProjectId,
  error,
  onRefresh,
}: GitStatusPanelProps) {
  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            Git Status / Diff
          </h3>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Read-only metadata from `workbench.git_status`.
          </p>
        </div>
        <button
          onClick={() => void onRefresh()}
          className="px-2.5 py-1.5 rounded-md text-xs"
          style={{ background: "var(--base-03)", color: "var(--text-secondary)" }}
          disabled={isLoading || !selectedProjectId}
        >
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          className="rounded-lg border-l-2 p-3 text-xs"
          style={{ borderColor: "var(--warning)", background: "rgba(245, 158, 11, 0.08)", color: "var(--text-secondary)" }}
        >
          {error}
        </div>
      )}

      {!selectedProjectId ? (
        <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Select a project to read git metadata.
        </p>
      ) : !gitStatus ? (
        <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Git data unavailable or not loaded yet.
        </p>
      ) : !gitStatus.is_git_repo ? (
        <p className="text-xs" style={{ color: "var(--warning)" }}>
          Selected project is not a git repository.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <Metric label="Branch" value={gitStatus.branch || "detached"} />
            <Metric label="Dirty" value={gitStatus.is_dirty ? "yes" : "no"} />
            <Metric label="Ahead/Behind" value={`${gitStatus.ahead}/${gitStatus.behind}`} />
            <Metric label="Recent" value={gitStatus.recent_commit || "none"} />
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Metric label="Staged" value={String(gitStatus.staged_count)} />
            <Metric label="Unstaged" value={String(gitStatus.unstaged_count)} />
            <Metric label="Untracked" value={String(gitStatus.untracked_count)} />
          </div>

          <div className="rounded-lg p-3 text-xs" style={{ background: "var(--base-01)" }}>
            <div style={{ color: "var(--text-tertiary)" }}>
              staged stat: {gitStatus.staged_diff_stat || "none"}
            </div>
            <div style={{ color: "var(--text-tertiary)" }}>
              unstaged stat: {gitStatus.unstaged_diff_stat || "none"}
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
              Changed files (first 20)
            </div>
            {gitStatus.changed_files.slice(0, 20).map((file) => (
              <div
                key={`${file.status}-${file.path}`}
                className="flex items-center justify-between text-xs rounded px-2 py-1"
                style={{ background: "var(--base-01)", color: "var(--text-secondary)" }}
              >
                <span style={{ fontFamily: "var(--font-mono)" }}>{file.path}</span>
                <span style={{ color: "var(--accent-primary)" }}>{file.status || "--"}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md p-2" style={{ background: "var(--base-01)" }}>
      <div style={{ color: "var(--text-tertiary)" }}>{label}</div>
      <div className="mt-1" style={{ color: "var(--text-primary)" }}>
        {value}
      </div>
    </div>
  );
}
