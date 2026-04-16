"use client";

import { useState, useEffect, useCallback } from 'react';
import { callMCPTool } from '@/lib/mcp-client';
import { TaskType, RoutingEntry } from '@/types/providers';

interface RoutingResponse {
  success: boolean;
  routing?: RoutingEntry[];
  error?: string;
  error_code?: string;
}

interface ActiveRoute {
  taskType: TaskType;
  primaryProvider: string | null;
  fallbackChain: string[];
  healthState: string;
  caveats: string | null;
}

export function useChatRouting() {
  const [routing, setRouting] = useState<RoutingEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRouting = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await callMCPTool('providers.routing') as RoutingResponse;
      if (response.success && response.routing) {
        setRouting(response.routing);
      } else {
        setError(response.error || 'Failed to get routing');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRouting();
  }, [fetchRouting]);

  const getActiveRoute = useCallback((taskType: TaskType): ActiveRoute | null => {
    const entry = routing.find(r => r.task_type === taskType);
    if (!entry) return null;

    return {
      taskType: entry.task_type as TaskType,
      primaryProvider: entry.primary_provider,
      fallbackChain: entry.fallback_chain || [],
      healthState: entry.health_state,
      caveats: entry.caveats,
    };
  }, [routing]);

  return {
    routing,
    isLoading,
    error,
    refresh: fetchRouting,
    getActiveRoute,
  };
}