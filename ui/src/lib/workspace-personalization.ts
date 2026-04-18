"use client";

export type WorkspacePreset = "guided" | "standard" | "expert";

export type HomeWidgetId =
  | "activeProject"
  | "recentThreads"
  | "servicesStatus"
  | "quickActions"
  | "securitySnapshot"
  | "activityFeed";

export interface WorkspacePersonalization {
  version: number;
  preset: WorkspacePreset;
  home: {
    visibleWidgets: HomeWidgetId[];
    widgetOrder: HomeWidgetId[];
  };
  chat: {
    sidebarOpen: boolean;
    showRuntimeDetails: boolean;
    showDiagnostics: boolean;
    showAdvanced: boolean;
  };
  updatedAt: string;
}

export const WORKSPACE_PERSONALIZATION_KEY = "bazzite-workspace-personalization-v1";
export const WORKSPACE_PERSONALIZATION_SEED_KEY = "bazzite-workspace-personalization-seed";

export const ALL_HOME_WIDGETS: HomeWidgetId[] = [
  "activeProject",
  "recentThreads",
  "servicesStatus",
  "quickActions",
  "securitySnapshot",
  "activityFeed",
];

export const PRESET_WIDGETS: Record<WorkspacePreset, HomeWidgetId[]> = {
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

export function defaultPersonalization(preset: WorkspacePreset = "standard"): WorkspacePersonalization {
  return {
    version: 1,
    preset,
    home: {
      visibleWidgets: [...PRESET_WIDGETS[preset]],
      widgetOrder: [...PRESET_WIDGETS[preset]],
    },
    chat: {
      sidebarOpen: true,
      showRuntimeDetails: preset === "expert",
      showDiagnostics: false,
      showAdvanced: preset === "expert",
    },
    updatedAt: new Date().toISOString(),
  };
}

function sanitizeWidgetList(input: unknown): HomeWidgetId[] {
  if (!Array.isArray(input)) {
    return [];
  }

  const deduped = new Set<HomeWidgetId>();
  for (const item of input) {
    if (typeof item === "string" && ALL_HOME_WIDGETS.includes(item as HomeWidgetId)) {
      deduped.add(item as HomeWidgetId);
    }
  }
  return [...deduped];
}

export function normalizePersonalization(input: unknown): WorkspacePersonalization {
  const defaults = defaultPersonalization("standard");
  const parsed = (input || {}) as Partial<WorkspacePersonalization>;

  const preset: WorkspacePreset =
    parsed.preset === "guided" || parsed.preset === "expert" || parsed.preset === "standard"
      ? parsed.preset
      : "standard";

  const fallback = defaultPersonalization(preset);
  const visibleWidgets = sanitizeWidgetList(parsed.home?.visibleWidgets);
  const orderWidgets = sanitizeWidgetList(parsed.home?.widgetOrder);

  const visibleSet = new Set(visibleWidgets.length > 0 ? visibleWidgets : fallback.home.visibleWidgets);
  const orderedVisible = [
    ...orderWidgets.filter((widgetId) => visibleSet.has(widgetId)),
    ...[...visibleSet].filter((widgetId) => !orderWidgets.includes(widgetId)),
  ];

  const chat = parsed.chat || fallback.chat;

  return {
    version: 1,
    preset,
    home: {
      visibleWidgets: [...visibleSet],
      widgetOrder: orderedVisible,
    },
    chat: {
      sidebarOpen: typeof chat.sidebarOpen === "boolean" ? chat.sidebarOpen : defaults.chat.sidebarOpen,
      showRuntimeDetails:
        typeof chat.showRuntimeDetails === "boolean"
          ? chat.showRuntimeDetails
          : fallback.chat.showRuntimeDetails,
      showDiagnostics:
        typeof chat.showDiagnostics === "boolean" ? chat.showDiagnostics : fallback.chat.showDiagnostics,
      showAdvanced: typeof chat.showAdvanced === "boolean" ? chat.showAdvanced : fallback.chat.showAdvanced,
    },
    updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : defaults.updatedAt,
  };
}

export function withPreset(
  current: WorkspacePersonalization,
  preset: WorkspacePreset
): WorkspacePersonalization {
  const next = defaultPersonalization(preset);
  return {
    ...current,
    preset,
    home: {
      visibleWidgets: [...next.home.visibleWidgets],
      widgetOrder: [...next.home.widgetOrder],
    },
    chat: {
      ...current.chat,
      showRuntimeDetails: next.chat.showRuntimeDetails,
      showDiagnostics: next.chat.showDiagnostics,
      showAdvanced: next.chat.showAdvanced,
    },
    updatedAt: new Date().toISOString(),
  };
}
