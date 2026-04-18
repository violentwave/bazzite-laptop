"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  defaultPersonalization,
  normalizePersonalization,
  withPreset,
  WORKSPACE_PERSONALIZATION_KEY,
  WORKSPACE_PERSONALIZATION_SEED_KEY,
  WorkspacePersonalization,
  WorkspacePreset,
  HomeWidgetId,
} from "@/lib/workspace-personalization";

type NoticeTone = "info" | "warning";

export interface PersistenceNotice {
  tone: NoticeTone;
  message: string;
}

function loadPersonalization(): {
  personalization: WorkspacePersonalization;
  notice: PersistenceNotice | null;
  persistenceAvailable: boolean;
} {
  const fallback = defaultPersonalization("standard");

  if (typeof window === "undefined") {
    return { personalization: fallback, notice: null, persistenceAvailable: true };
  }

  try {
    const raw = window.localStorage.getItem(WORKSPACE_PERSONALIZATION_KEY);
    const seed = window.localStorage.getItem(WORKSPACE_PERSONALIZATION_SEED_KEY);

    if (!raw) {
      if (seed === "1") {
        return {
          personalization: fallback,
          notice: {
            tone: "warning",
            message:
              "Workspace personalization data was unavailable or cleared. Falling back to Standard preset.",
          },
          persistenceAvailable: true,
        };
      }
      return { personalization: fallback, notice: null, persistenceAvailable: true };
    }

    const parsed = JSON.parse(raw);
    return {
      personalization: normalizePersonalization(parsed),
      notice: null,
      persistenceAvailable: true,
    };
  } catch {
    return {
      personalization: fallback,
      notice: {
        tone: "warning",
        message:
          "Workspace personalization storage is unavailable. Running with Standard preset only for this session.",
      },
      persistenceAvailable: false,
    };
  }
}

function savePersonalization(next: WorkspacePersonalization): boolean {
  if (typeof window === "undefined") {
    return true;
  }

  try {
    window.localStorage.setItem(WORKSPACE_PERSONALIZATION_KEY, JSON.stringify(next));
    window.localStorage.setItem(WORKSPACE_PERSONALIZATION_SEED_KEY, "1");
    return true;
  } catch {
    return false;
  }
}

export function useWorkspacePersonalization() {
  const initial = useMemo(() => loadPersonalization(), []);
  const [personalization, setPersonalization] = useState<WorkspacePersonalization>(
    initial.personalization
  );
  const [persistenceAvailable, setPersistenceAvailable] = useState(initial.persistenceAvailable);
  const [notice, setNotice] = useState<PersistenceNotice | null>(initial.notice);

  useEffect(() => {
    const handler = (event: StorageEvent) => {
      if (event.key !== WORKSPACE_PERSONALIZATION_KEY) {
        return;
      }

      const loaded = loadPersonalization();
      setPersonalization(loaded.personalization);
      setPersistenceAvailable(loaded.persistenceAvailable);
      if (loaded.notice) {
        setNotice(loaded.notice);
      }
    };

    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const updatePersonalization = useCallback(
    (updater: (current: WorkspacePersonalization) => WorkspacePersonalization) => {
      setPersonalization((current) => {
        const next = updater(current);
        const persisted = savePersonalization(next);
        if (!persisted) {
          setPersistenceAvailable(false);
          setNotice({
            tone: "warning",
            message:
              "Workspace personalization could not be saved locally. Falling back to Standard preset on next reload.",
          });
          return current;
        }
        setPersistenceAvailable(true);
        return next;
      });
    },
    []
  );

  const setPreset = useCallback(
    (preset: WorkspacePreset) => {
      updatePersonalization((current) => withPreset(current, preset));
    },
    [updatePersonalization]
  );

  const setHomeWidgets = useCallback(
    (visibleWidgets: HomeWidgetId[], widgetOrder: HomeWidgetId[]) => {
      updatePersonalization((current) => ({
        ...current,
        home: {
          visibleWidgets,
          widgetOrder,
        },
        updatedAt: new Date().toISOString(),
      }));
    },
    [updatePersonalization]
  );

  const setChatVisibility = useCallback(
    (patch: Partial<WorkspacePersonalization["chat"]>) => {
      updatePersonalization((current) => ({
        ...current,
        chat: {
          ...current.chat,
          ...patch,
        },
        updatedAt: new Date().toISOString(),
      }));
    },
    [updatePersonalization]
  );

  const clearPersonalization = useCallback(() => {
    const fallback = defaultPersonalization("standard");
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(WORKSPACE_PERSONALIZATION_KEY);
        window.localStorage.setItem(WORKSPACE_PERSONALIZATION_SEED_KEY, "1");
      } catch {
        // Ignore and still reset in-memory preferences.
      }
    }

    setPersonalization(fallback);
    setPersistenceAvailable(true);
    setNotice({
      tone: "info",
      message: "Workspace personalization was cleared. Standard preset is active.",
    });
  }, []);

  return {
    personalization,
    preset: personalization.preset,
    persistenceAvailable,
    notice,
    dismissNotice: () => setNotice(null),
    setPreset,
    setHomeWidgets,
    setChatVisibility,
    clearPersonalization,
  };
}
