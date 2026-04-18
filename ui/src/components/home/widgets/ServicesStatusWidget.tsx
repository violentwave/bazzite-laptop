"use client";

import { useCallback, useMemo } from "react";
import { WidgetContainer } from "./WidgetContainer";
import { useProviders } from "@/hooks/useProviders";
import { useSecurity } from "@/hooks/useSecurity";
import { summarizeRuntimeOverview, summarizeSecurityWidget } from "@/lib/home-dashboard";
import { buildHomeSystemStatus } from "@/lib/console-simplify";

type ServicesStatusWidgetProps = {
  onDetailClick?: () => void;
  onRemove?: () => void;
};

export function ServicesStatusWidget({
  onDetailClick,
  onRemove,
}: ServicesStatusWidgetProps = {}) {
  const {
    providers,
    models,
    counts,
    isLoading: providersLoading,
    error: providersError,
    lastRefresh: providersLastRefresh,
  } = useProviders();
  const {
    overview,
    alerts,
    findings,
    systemHealth,
    isLoading: securityLoading,
    error: securityError,
    partialData,
    missingSources,
  } = useSecurity();

  const runtimeSummary = useMemo(() => summarizeRuntimeOverview(counts, providers, models), [counts, providers, models]);
  const securitySummary = useMemo(() => summarizeSecurityWidget(overview, alerts, findings, systemHealth), [overview, alerts, findings, systemHealth]);
  const systemStatusModel = useMemo(
    () =>
      buildHomeSystemStatus({
        securitySummary,
        runtimeSummary,
        securityLoading,
        providersLoading,
        securityError,
        providersError,
        partialData,
        missingSources,
      }),
    [
      missingSources,
      partialData,
      providersError,
      providersLoading,
      runtimeSummary,
      securityError,
      securityLoading,
      securitySummary,
    ]
  );

  const formatRelativeTime = useCallback((timestamp: string | null): string => {
    if (!timestamp) {
      return "never";
    }
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

  // Get the last refresh time as a string or null
  const getLastRefreshTimeString = useCallback(() => {
    if (!providersLastRefresh) {
      return null;
    }
    // If it's a Date object, convert to ISO string; if it's already a string, use as is
    return providersLastRefresh instanceof Date ? providersLastRefresh.toISOString() : providersLastRefresh;
  }, [providersLastRefresh]);

  if (providersLoading || securityLoading) {
    return (
      <WidgetContainer
        title="Services Status"
        subtitle="Live health of core services"
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
      title="Services Status"
      subtitle="Live health of core services"
      onConfigure={onDetailClick}
      onRemove={onRemove}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-tertiary">System Status</span>
          <span
            className="px-2 py-1 rounded text-xs"
            style={{
              border: "1px solid var(--base-4)",
              background: "var(--base-1)",
              color:
                systemStatusModel.tone === "danger"
                  ? "var(--danger)"
                  : systemStatusModel.tone === "warning"
                    ? "var(--warning)"
                    : systemStatusModel.tone === "success"
                      ? "var(--success)"
                      : "var(--text-tertiary)",
            }}
          >
            {systemStatusModel.title}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Critical</div>
            <div className="text-base font-semibold text-danger">{securitySummary.critical}</div>
          </div>
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Alerts</div>
            <div className="text-base font-semibold text-warning">{securitySummary.alerts}</div>
          </div>
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Healthy</div>
            <div className="text-base font-semibold text-success">{runtimeSummary.healthy}</div>
          </div>
          <div className="rounded-lg px-3 py-2 border border-base-4 bg-base-1">
            <div className="text-xs text-tertiary">Degraded</div>
            <div className="text-base font-semibold text-warning">
              {runtimeSummary.degraded + runtimeSummary.blocked}
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-tertiary">Providers</span>
            <span className="text-xs text-tertiary">
              {providers.length} configured ({counts?.healthy ?? 0} healthy)
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-tertiary">Models</span>
            <span className="text-xs text-tertiary">
              {models.filter((m) => m.is_available !== false).length} available
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-tertiary">Last Scan</span>
            <span className="text-xs text-tertiary">
              {formatRelativeTime(securitySummary.lastScan)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-tertiary">Last Refresh</span>
            <span className="text-xs text-tertiary">
              {formatRelativeTime(getLastRefreshTimeString())}
            </span>
          </div>
        </div>

        {!providersError && !securityError && (providers.length > 0 || models.length > 0) && (
          <div className="mt-3 pt-3 border-t border-base-4">
            <div className="flex flex-wrap gap-4">
              {providers
                .filter((p) => p.is_configured)
                .slice(0, 4)
                .map((provider) => (
                  <div key={provider.id} className="flex items-center gap-2 text-xs">
                    <div className="h-2 w-2 rounded-full" style={{ background: provider.is_healthy ? "var(--success)" : "var(--danger)" }}></div>
                    <span className="truncate max-w-xs">{provider.name}</span>
                  </div>
                ))}
              {models
                .filter((m) => m.is_available !== false)
                .slice(0, 4)
                .map((model) => (
                  <div key={model.id} className="flex items-center gap-2 text-xs">
                    <div className="h-2 w-2 rounded-full" style={{ background: model.is_available ? "var(--success)" : "var(--warning)" }}></div>
                    <span className="truncate max-w-xs">{model.name}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {providersError || securityError && (
          <div className="mt-3 p-3 rounded-lg border border-base-4 bg-base-1/50">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ background: "var(--danger)" }}></div>
              <span className="text-sm text-danger">
                {(providersError ? "Providers error: " : "")}{(securityError ? "Security error: " : "")}{providersError || securityError}
              </span>
            </div>
          </div>
        )}
      </div>
    </WidgetContainer>
  );
}
