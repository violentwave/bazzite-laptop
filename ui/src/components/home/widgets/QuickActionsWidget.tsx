"use client";

import { useCallback } from "react";
import { WidgetContainer } from "./WidgetContainer";
import { useShell } from "@/components/shell/ShellContext";

type QuickActionsWidgetProps = {
  onRemove?: () => void;
};

export function QuickActionsWidget({
  onRemove,
}: QuickActionsWidgetProps = {}) {
  const { setActivePanel } = useShell();

  return (
    <WidgetContainer
      title="Quick Actions"
      subtitle="Jump directly into focused operator surfaces"
      onRemove={onRemove}
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <button
          onClick={() => setActivePanel("chat")}
          className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-1"
          style={{
            border: "1px solid var(--base-4)",
            color: "var(--text-primary)",
          }}
        >
          Chat Workspace
        </button>
        <button
          onClick={() => setActivePanel("security")}
          className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-1"
          style={{
            border: "1px solid var(--base-4)",
            color: "var(--text-primary)",
          }}
        >
          Security Ops
        </button>
        <button
          onClick={() => setActivePanel("tools")}
          className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-1"
          style={{
            border: "1px solid var(--base-4)",
            color: "var(--text-primary)",
          }}
        >
          Tools
        </button>
        <button
          onClick={() => setActivePanel("models")}
          className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-1"
          style={{
            border: "1px solid var(--base-4)",
            color: "var(--text-primary)",
          }}
        >
          Providers
        </button>
        <button
          onClick={() => setActivePanel("projects")}
          className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-1"
          style={{
            border: "1px solid var(--base-4)",
            color: "var(--text-primary)",
          }}
        >
          Projects
        </button>
        <button
          onClick={() => setActivePanel("workbench")}
          className="rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-base-1"
          style={{
            border: "1px solid var(--base-4)",
            color: "var(--text-primary)",
          }}
        >
          Workbench
        </button>
      </div>
    </WidgetContainer>
  );
}
