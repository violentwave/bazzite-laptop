"use client";

import { useCallback, useMemo, useState } from "react";
import { useShell } from "@/components/shell/ShellContext";
import { ActiveProjectWidget } from "@/components/home/widgets/ActiveProjectWidget";
import { RecentThreadsWidget } from "@/components/home/widgets/RecentThreadsWidget";
import { ServicesStatusWidget } from "@/components/home/widgets/ServicesStatusWidget";
import { QuickActionsWidget } from "@/components/home/widgets/QuickActionsWidget";
import { SecuritySnapshotWidget } from "@/components/home/widgets/SecuritySnapshotWidget";
import { ActivityFeedWidget } from "@/components/home/widgets/ActivityFeedWidget";
import { useWorkspacePersonalization } from "@/hooks/useWorkspacePersonalization";
import {
  HomeWidgetId,
  WorkspacePreset,
  PRESET_WIDGETS,
} from "@/lib/workspace-personalization";

const WIDGET_LABELS: Record<HomeWidgetId, { name: string; description: string }> = {
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
  const [isAddWidgetOpen, setIsAddWidgetOpen] = useState(false);
  const {
    preset,
    personalization,
    notice,
    dismissNotice,
    setPreset,
    setHomeWidgets,
    clearPersonalization,
  } = useWorkspacePersonalization();

  const orderedVisibleWidgets = useMemo(() => {
    const visibleSet = new Set(personalization.home.visibleWidgets);
    return [
      ...personalization.home.widgetOrder.filter((widgetId) => visibleSet.has(widgetId)),
      ...personalization.home.visibleWidgets.filter(
        (widgetId) => !personalization.home.widgetOrder.includes(widgetId)
      ),
    ];
  }, [personalization.home.visibleWidgets, personalization.home.widgetOrder]);

  const availableWidgets = useMemo(
    () => (Object.keys(WIDGET_LABELS) as HomeWidgetId[]).filter((id) => !orderedVisibleWidgets.includes(id)),
    [orderedVisibleWidgets]
  );

  const setPresetWithDefaults = useCallback(
    (nextPreset: WorkspacePreset) => {
      setPreset(nextPreset);
    },
    [setPreset]
  );

  const addWidget = useCallback(
    (widgetId: HomeWidgetId) => {
      const visible = personalization.home.visibleWidgets.includes(widgetId)
        ? personalization.home.visibleWidgets
        : [...personalization.home.visibleWidgets, widgetId];

      const order = personalization.home.widgetOrder.includes(widgetId)
        ? personalization.home.widgetOrder
        : [...personalization.home.widgetOrder, widgetId];

      setHomeWidgets(visible, order);
    },
    [personalization.home.visibleWidgets, personalization.home.widgetOrder, setHomeWidgets]
  );

  const removeWidget = useCallback(
    (widgetId: HomeWidgetId) => {
      const visible = personalization.home.visibleWidgets.filter((id) => id !== widgetId);
      const order = personalization.home.widgetOrder.filter((id) => id !== widgetId);
      setHomeWidgets(visible, order);
    },
    [personalization.home.visibleWidgets, personalization.home.widgetOrder, setHomeWidgets]
  );

  const moveWidget = useCallback(
    (widgetId: HomeWidgetId, direction: "up" | "down") => {
      const current = [...orderedVisibleWidgets];
      const index = current.indexOf(widgetId);
      if (index < 0) return;

      const target = direction === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= current.length) return;

      const [moved] = current.splice(index, 1);
      current.splice(target, 0, moved);
      setHomeWidgets([...personalization.home.visibleWidgets], current);
    },
    [orderedVisibleWidgets, personalization.home.visibleWidgets, setHomeWidgets]
  );

  const resetToPreset = useCallback(() => {
    const defaults = PRESET_WIDGETS[preset];
    setHomeWidgets([...defaults], [...defaults]);
  }, [preset, setHomeWidgets]);

  const renderWidget = (widgetId: HomeWidgetId) => {
    const index = orderedVisibleWidgets.indexOf(widgetId);

    return (
      <div key={widgetId} className="space-y-2">
        <div className="flex items-center justify-end gap-1">
          <button
            className="rounded px-2 py-1 text-[11px]"
            style={{
              background: "var(--base-01)",
              color: "var(--text-secondary)",
              border: "1px solid var(--base-04)",
              opacity: index <= 0 ? 0.5 : 1,
            }}
            onClick={() => moveWidget(widgetId, "up")}
            disabled={index <= 0}
            title="Move widget earlier"
          >
            Move up
          </button>
          <button
            className="rounded px-2 py-1 text-[11px]"
            style={{
              background: "var(--base-01)",
              color: "var(--text-secondary)",
              border: "1px solid var(--base-04)",
              opacity: index >= orderedVisibleWidgets.length - 1 ? 0.5 : 1,
            }}
            onClick={() => moveWidget(widgetId, "down")}
            disabled={index >= orderedVisibleWidgets.length - 1}
            title="Move widget later"
          >
            Move down
          </button>
        </div>

        {widgetId === "activeProject" && (
          <ActiveProjectWidget
            onOpenInChat={() => setActivePanel("chat")}
            onOpenInWorkbench={() => setActivePanel("workbench")}
            onRemove={() => removeWidget("activeProject")}
          />
        )}
        {widgetId === "recentThreads" && (
          <RecentThreadsWidget onRemove={() => removeWidget("recentThreads")} />
        )}
        {widgetId === "servicesStatus" && (
          <ServicesStatusWidget onRemove={() => removeWidget("servicesStatus")} />
        )}
        {widgetId === "quickActions" && (
          <QuickActionsWidget onRemove={() => removeWidget("quickActions")} />
        )}
        {widgetId === "securitySnapshot" && (
          <SecuritySnapshotWidget onRemove={() => removeWidget("securitySnapshot")} />
        )}
        {widgetId === "activityFeed" && (
          <ActivityFeedWidget onRemove={() => removeWidget("activityFeed")} />
        )}
      </div>
    );
  };

  return (
    <div className="h-full overflow-auto px-6 py-6">
      {notice && (
        <div
          className="mb-4 rounded-lg px-3 py-2 flex items-start justify-between gap-3"
          style={{
            background: notice.tone === "warning" ? "rgba(245, 158, 11, 0.12)" : "rgba(14, 165, 233, 0.12)",
            border: `1px solid ${notice.tone === "warning" ? "rgba(245, 158, 11, 0.35)" : "rgba(14, 165, 233, 0.35)"}`,
            color: notice.tone === "warning" ? "var(--warning)" : "var(--live-cyan)",
          }}
        >
          <p className="text-sm">{notice.message}</p>
          <button
            onClick={dismissNotice}
            className="rounded px-2 py-1 text-xs"
            style={{ border: "1px solid var(--base-04)", color: "var(--text-secondary)", background: "var(--base-01)" }}
          >
            Dismiss
          </button>
        </div>
      )}

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
            onChange={(event) => setPresetWithDefaults(event.target.value as WorkspacePreset)}
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

          <button
            onClick={clearPersonalization}
            className="rounded-lg px-3 py-2 text-sm"
            style={{
              background: "var(--base-01)",
              color: "var(--warning)",
              border: "1px solid var(--base-04)",
            }}
          >
            Clear Personalization
          </button>
        </div>
      </div>

      <div className="mb-4 rounded-lg px-3 py-2 text-xs" style={{ background: "var(--base-01)", border: "1px solid var(--base-04)", color: "var(--text-tertiary)" }}>
        Preset: <span style={{ color: "var(--text-primary)" }}>{preset}</span> · Visible widgets: {orderedVisibleWidgets.length} · Reorder with move controls.
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {orderedVisibleWidgets.map((widgetId) => renderWidget(widgetId))}
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
                Preset defaults: Guided (3 widgets), Standard (5 widgets), Expert (6 widgets). Layout changes persist locally.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
