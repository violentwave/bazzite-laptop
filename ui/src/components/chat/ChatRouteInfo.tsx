"use client";

import { useChatRouting } from '@/hooks/useChatRouting';
import { TaskType } from '@/types/providers';

interface ChatRouteInfoProps {
  selectedProfile: TaskType;
}

export function ChatRouteInfo({ selectedProfile }: ChatRouteInfoProps) {
  const { getActiveRoute, isLoading, error } = useChatRouting();
  const activeRoute = getActiveRoute(selectedProfile);

  if (isLoading) {
    return (
      <div className="text-xs flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
        <span className="animate-pulse">Loading route...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-xs" style={{ color: 'var(--danger)' }}>
        Route error
      </div>
    );
  }

  if (!activeRoute) {
    return null;
  }

  const getHealthColor = (state: string) => {
    if (state?.includes('auth-broken') || state?.includes('blocked')) {
      return 'var(--danger)';
    }
    if (state?.includes('degraded') || state?.includes('cooldown')) {
      return 'var(--warning)';
    }
    if (state?.includes('no-provider')) {
      return 'var(--text-tertiary)';
    }
    return 'var(--live-cyan)';
  };

  return (
    <div className="text-xs flex items-center gap-2" style={{ color: 'var(--text-tertiary)' }}>
      <span>Route:</span>
      <span style={{ color: getHealthColor(activeRoute.healthState) }}>
        {activeRoute.primaryProvider || 'none'}
      </span>
      {activeRoute.fallbackChain.length > 0 && (
        <>
          <span>→</span>
          <span>{activeRoute.fallbackChain.join(', ')}</span>
        </>
      )}
      {activeRoute.caveats && (
        <span className="italic" title={activeRoute.caveats}>
          ({activeRoute.caveats})
        </span>
      )}
    </div>
  );
}