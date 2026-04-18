"use client";

import { WidgetContainer } from "./WidgetContainer";
import { useSecurityAutopilot } from "@/hooks/useSecurityAutopilot";

type ActivityFeedWidgetProps = {
  onRemove?: () => void;
};

export function ActivityFeedWidget({ onRemove }: ActivityFeedWidgetProps = {}) {
  const { auditEvents, isLoading, error } = useSecurityAutopilot();

  if (isLoading) {
    return (
      <WidgetContainer
        title="Activity Feed"
        subtitle="Recent operator and system events"
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
      title="Activity Feed" 
      subtitle="Recent operator and system events"
      onRemove={onRemove}
    >
      <div className="space-y-3 max-h-[300px] overflow-auto pr-2 custom-scrollbar">
        {auditEvents.length === 0 ? (
          <div className="text-sm px-3 py-2 rounded-lg border border-base-4 bg-base-1 text-tertiary text-center">
            No recent activity detected.
          </div>
        ) : (
          auditEvents.slice(0, 10).map((event, i) => (
            <div 
              key={i} 
              className="text-xs p-2 rounded border border-base-4 bg-base-1"
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-medium text-primary uppercase">{event.event_type?.replace(/_/g, ' ') || 'SYSTEM EVENT'}</span>
                <span className="text-tertiary">
                  {event.created_at ? new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'unknown'}
                </span>
              </div>
              <div className="text-secondary line-clamp-2">
                {formatEventSummary(event.payload)}
              </div>
              {event.actor && (
                <div className="mt-1 text-tertiary">
                  Actor: <span className="text-secondary">{event.actor}</span>
                </div>
              )}
            </div>
          ))
        )}
        {error && (
          <div className="text-xs text-danger mt-2">
            Error: {error}
          </div>
        )}
      </div>
    </WidgetContainer>
  );
}

function formatEventSummary(payload: Record<string, unknown> | undefined): string {
  if (!payload) {
    return "No additional details";
  }

  const summary = payload.summary;
  if (typeof summary === "string" && summary.length > 0) {
    return summary;
  }

  const message = payload.message;
  if (typeof message === "string" && message.length > 0) {
    return message;
  }

  try {
    return JSON.stringify(payload).slice(0, 120);
  } catch {
    return "Details unavailable";
  }
}
