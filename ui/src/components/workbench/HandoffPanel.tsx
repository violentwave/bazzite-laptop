"use client";

import { useState } from "react";
import { WorkbenchHandoffNote } from "@/types/agent-workbench";

function redactArtifact(path: string): string {
  const clean = path.replace(/\\/g, "/");
  const parts = clean.split("/").filter(Boolean);
  if (parts.length <= 3) {
    return clean;
  }
  return `.../${parts.slice(-3).join("/")}`;
}

interface HandoffPanelProps {
  selectedSessionId: string | null;
  notes: WorkbenchHandoffNote[];
  isSaving: boolean;
  error: string | null;
  onSave: (summary: string, artifacts: string[], phase: string) => Promise<void>;
}

export function HandoffPanel({
  selectedSessionId,
  notes,
  isSaving,
  error,
  onSave,
}: HandoffPanelProps) {
  const [summary, setSummary] = useState("");
  const [artifactsText, setArtifactsText] = useState("");
  const [phase, setPhase] = useState("P124");

  const handleSave = async () => {
    if (!summary.trim()) {
      return;
    }
    const artifacts = artifactsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    await onSave(summary.trim(), artifacts, phase.trim() || "P124");
    setSummary("");
    setArtifactsText("");
  };

  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
    >
      <div>
        <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Handoff Notes + Artifacts
        </h3>
        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
          Saves structured handoff notes via `workbench.handoff_note`.
        </p>
      </div>

      {error && (
        <div
          className="rounded-lg border-l-2 p-3 text-xs"
          style={{ borderColor: "var(--warning)", background: "rgba(245, 158, 11, 0.08)", color: "var(--text-secondary)" }}
        >
          {error}
        </div>
      )}

      <label className="block text-xs" style={{ color: "var(--text-tertiary)" }}>
        Phase
        <input
          type="text"
          value={phase}
          onChange={(event) => setPhase(event.target.value)}
          className="mt-1 w-full px-2 py-2 rounded-md text-sm"
          style={{
            background: "var(--base-01)",
            border: "1px solid var(--base-04)",
            color: "var(--text-primary)",
          }}
        />
      </label>

      <label className="block text-xs" style={{ color: "var(--text-tertiary)" }}>
        Summary
        <textarea
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          className="mt-1 w-full px-2 py-2 rounded-md text-sm min-h-[86px]"
          style={{
            background: "var(--base-01)",
            border: "1px solid var(--base-04)",
            color: "var(--text-primary)",
          }}
          placeholder="Describe session results, blockers, and next actions"
        />
      </label>

      <label className="block text-xs" style={{ color: "var(--text-tertiary)" }}>
        Artifact paths (comma-separated)
        <input
          type="text"
          value={artifactsText}
          onChange={(event) => setArtifactsText(event.target.value)}
          className="mt-1 w-full px-2 py-2 rounded-md text-sm"
          style={{
            background: "var(--base-01)",
            border: "1px solid var(--base-04)",
            color: "var(--text-primary)",
          }}
          placeholder="docs/evidence/p124/..., docs/P124_PLAN.md"
        />
      </label>

      <div className="flex items-center justify-between gap-2">
        <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          session={selectedSessionId || "none attached"}
        </div>
        <button
          onClick={() => void handleSave()}
          className="px-3 py-1.5 rounded-md text-xs"
          style={{ background: "var(--accent-primary)", color: "white" }}
          disabled={isSaving || !summary.trim()}
        >
          {isSaving ? "Saving..." : "Save Handoff"}
        </button>
      </div>

      {notes.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
            Recent notes (local UI cache)
          </div>
          {notes.slice(0, 5).map((note) => (
            <div
              key={`${note.timestamp}-${note.summary}`}
              className="rounded-lg border p-2"
              style={{ borderColor: "var(--base-04)", background: "var(--base-01)" }}
            >
              <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                {note.timestamp} · {note.phase}
              </div>
              <div className="text-sm mt-1" style={{ color: "var(--text-primary)" }}>
                {note.summary}
              </div>
              {note.artifacts.length > 0 && (
                <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                  artifacts: {note.artifacts.map((item) => redactArtifact(item)).join(", ")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
