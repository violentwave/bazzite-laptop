"use client";

import { ArtifactInfo } from "@/types/project-workflow";
import { formatBytes, formatTimestamp } from "@/hooks/useProjectWorkflow";

interface ArtifactHistoryPanelProps {
  artifacts: ArtifactInfo[];
  isLoading: boolean;
}

export function ArtifactHistoryPanel({ artifacts, isLoading }: ArtifactHistoryPanelProps) {
  if (isLoading) {
    return (
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="text-xs font-medium uppercase tracking-wide mb-3"
          style={{ color: "var(--text-tertiary)" }}
        >
          Recent Artifacts
        </h3>
        <div className="animate-pulse space-y-2">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-10 rounded"
              style={{ background: "var(--base-03)" }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3
          className="text-xs font-medium uppercase tracking-wide"
          style={{ color: "var(--text-tertiary)" }}
        >
          Recent Artifacts
        </h3>
        <span
          className="text-xs px-2 py-0.5 rounded-full"
          style={{
            background: "var(--base-03)",
            color: "var(--text-secondary)",
          }}
        >
          {artifacts.length}
        </span>
      </div>

      {artifacts.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
          No artifacts generated yet
        </p>
      ) : (
        <div className="space-y-2">
          {artifacts.slice(0, 5).map((artifact, index) => (
            <div
              key={index}
              className="flex items-center gap-3 p-2 rounded border cursor-pointer transition-colors hover:bg-opacity-50"
              style={{
                background: "var(--base-01)",
                borderColor: "var(--base-04)",
              }}
            >
              {/* File Icon */}
              <div
                className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--base-03)" }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>

              {/* Artifact Info */}
              <div className="flex-1 min-w-0">
                <div
                  className="text-sm font-medium truncate"
                  style={{ color: "var(--text-primary)" }}
                >
                  {artifact.name}
                </div>
                <div
                  className="text-xs flex items-center gap-2"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  <span>{formatBytes(artifact.size_bytes)}</span>
                  {artifact.source_phase && (
                    <>
                      <span>•</span>
                      <span
                        className="font-mono"
                        style={{ color: "var(--accent-primary)" }}
                      >
                        {artifact.source_phase}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Timestamp */}
              <div
                className="text-xs flex-shrink-0"
                style={{ color: "var(--text-tertiary)" }}
              >
                {formatTimestamp(artifact.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
