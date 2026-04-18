"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useShell } from "@/components/shell/ShellContext";
import { ActiveProjectWidget } from "@/components/home/widgets/ActiveProjectWidget";
import { RecentThreadsWidget } from "@/components/home/widgets/RecentThreadsWidget";
import { ServicesStatusWidget } from "@/components/home/widgets/ServicesStatusWidget";
import { QuickActionsWidget } from "@/components/home/widgets/QuickActionsWidget";
import { SecuritySnapshotWidget } from "@/components/home/widgets/SecuritySnapshotWidget";
import { ActivityFeedWidget } from "@/components/home/widgets/ActivityFeedWidget";

type HomePreset = "guided" | "standard" | "expert";

type WidgetId =
  | "activeProject"
  | "recentThreads"
  | "servicesStatus"
  | "quickActions"
  | "securitySnapshot"
  | "activityFeed";

const PRESET_WIDGETS: Record<HomePreset, WidgetId[]> = {
  guided: ["activeProject", "recentThreads", "servicesStatus"],
  standard: ["activeProject", "recentThreads", "servicesStatus", "quickActions", "securitySnapshot"],
  expert: [
    "activeProject",
    "recentThreads",
    "servicesStatus",
    "quickActions",
    "securitySnapshot",
    "activityFeed",
  ],
};

const WIDGET_LABELS: Record<WidgetId, { name: string; description: string }> = {
  activeProject: {
    name: "Active Project",
    description: "Primary project entry and launch controls",
  },
  recentThreads: {
    name: "Recent Threads",
    description: "Resume local chat work quickly",
  },
  servicesStatus: {
    name: "Services Status",
    description: "Runtime and provider health summaries",
  },
  quickActions: {
    name: "Quick Actions",
    description: "Jump to key operator surfaces",
  },
  securitySnapshot: {
    name: "Security Snapshot",
    description: "Alert and finding summary",
  },
  activityFeed: {
    name: "Activity Feed",
    description: "Recent operator and system events",
  },
};

export function HomeContainer() {
  const { setActivePanel } = useShell();
  const [preset, setPreset] = useState<HomePreset>("standard");
  const [visibleWidgets, setVisibleWidgets] = useState<WidgetId[]>(PRESET_WIDGETS.standard);
  const [isAddWidgetOpen, setIsAddWidgetOpen] = useState(false);

  useEffect(() => {
    setVisibleWidgets(PRESET_WIDGETS[preset]);
  }, [preset]);

  const addWidget = useCallback((widgetId: WidgetId) => {
    setVisibleWidgets((current) => {
      if (current.includes(widgetId)) {
        return current;
      }
      return [...current, widgetId];
    });
  }, []);

  const removeWidget = useCallback((widgetId: WidgetId) => {
    setVisibleWidgets((current) => current.filter((id) => id !== widgetId));
  }, []);

  const resetToPreset = useCallback(() => {
    setVisibleWidgets(PRESET_WIDGETS[preset]);
  }, [preset]);

  const availableWidgets = useMemo(
    () => (Object.keys(WIDGET_LABELS) as WidgetId[]).filter((id) => !visibleWidgets.includes(id)),
    [visibleWidgets]
  );

  return (
    <div className="h-full overflow-auto px-6 py-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
            Home Dashboard
          </h2>
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            Calm, widget-based control surface for project entry and live runtime truth.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="home-preset-select">
            Home preset
          </label>
          <select
            id="home-preset-select"
            value={preset}
            onChange={(event) => setPreset(event.target.value as HomePreset)}
            className="rounded-lg px-3 py-2 text-sm"
            style={{
              background: "var(--base-02)",
              color: "var(--text-primary)",
              border: "1px solid var(--base-04)",
            }}
          >
            <option value="guided">Guided</option>
            <option value="standard">Standard</option>
            <option value="expert">Expert</option>
          </select>

          <button
            onClick={() => setIsAddWidgetOpen(true)}
            className="rounded-lg px-3 py-2 text-sm"
            style={{
              background: "var(--base-02)",
              color: "var(--text-primary)",
              border: "1px solid var(--base-04)",
            }}
          >
            Add Widget
          </button>

          <button
            onClick={resetToPreset}
            className="rounded-lg px-3 py-2 text-sm"
            style={{
              background: "var(--base-01)",
              color: "var(--text-secondary)",
              border: "1px solid var(--base-04)",
            }}
          >
            Reset Layout
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {visibleWidgets.includes("activeProject") && (
          <ActiveProjectWidget
            onOpenInChat={() => setActivePanel("chat")}
            onOpenInWorkbench={() => setActivePanel("workbench")}
            onRemove={() => removeWidget("activeProject")}
          />
        )}

        {visibleWidgets.includes("recentThreads") && (
          <RecentThreadsWidget onRemove={() => removeWidget("recentThreads")} />
        )}

        {visibleWidgets.includes("servicesStatus") && (
          <ServicesStatusWidget onRemove={() => removeWidget("servicesStatus")} />
        )}

        {visibleWidgets.includes("quickActions") && (
          <QuickActionsWidget onRemove={() => removeWidget("quickActions")} />
        )}

        {visibleWidgets.includes("securitySnapshot") && (
          <SecuritySnapshotWidget onRemove={() => removeWidget("securitySnapshot")} />
        )}

        {visibleWidgets.includes("activityFeed") && (
          <ActivityFeedWidget onRemove={() => removeWidget("activityFeed")} />
        )}
      </div>

      {isAddWidgetOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0, 0, 0, 0.45)" }}
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setIsAddWidgetOpen(false);
            }
          }}
        >
          <div
            className="w-full max-w-lg rounded-xl p-4"
            style={{
              background: "var(--base-02)",
              border: "1px solid var(--base-04)",
              boxShadow: "var(--shadow-xl)",
            }}
          >
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Add Widget
              </h4>
              <button
                onClick={() => setIsAddWidgetOpen(false)}
                className="rounded px-2 py-1 text-xs"
                style={{
                  background: "var(--base-01)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--base-04)",
                }}
              >
                Close
              </button>
            </div>

            {availableWidgets.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                All widgets are already visible for this layout.
              </p>
            ) : (
              <div className="space-y-2">
                {availableWidgets.map((widgetId) => (
                  <div
                    key={widgetId}
                    className="flex items-center justify-between rounded-lg px-3 py-2"
                    style={{
                      border: "1px solid var(--base-04)",
                      background: "var(--base-01)",
                    }}
                  >
                    <div>
                      <div className="text-sm" style={{ color: "var(--text-primary)" }}>
                        {WIDGET_LABELS[widgetId].name}
                      </div>
                      <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                        {WIDGET_LABELS[widgetId].description}
                      </div>
                    </div>
                    <button
                      onClick={() => addWidget(widgetId)}
                      className="rounded-lg px-3 py-1.5 text-sm"
                      style={{
                        background: "var(--accent-primary)",
                        color: "white",
                      }}
                    >
                      Add
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-3 border-t pt-3" style={{ borderColor: "var(--base-04)" }}>
              <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                Preset defaults: Guided (3 widgets), Standard (5 widgets), Expert (6 widgets).
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
