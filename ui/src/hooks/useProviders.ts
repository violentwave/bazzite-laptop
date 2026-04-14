"use client";

import { useState, useEffect, useCallback } from 'react';
import { ProviderInfo, ModelInfo, RoutingEntry, ProviderHealth } from '@/types/providers';
import { callMCPTool } from '@/lib/mcp-client';

interface UseProvidersReturn {
  providers: ProviderInfo[];
  models: ModelInfo[];
  routing: RoutingEntry[];
  health: Record<string, ProviderHealth>;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastRefresh: Date | null;
}

export function useProviders(): UseProvidersReturn {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [routing, setRouting] = useState<RoutingEntry[]>([]);
  const [health, setHealth] = useState<Record<string, ProviderHealth>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [providersData, modelsData, routingData, healthData] = await Promise.all([
        callMCPTool('providers.discover'),
        callMCPTool('providers.models'),
        callMCPTool('providers.routing'),
        callMCPTool('providers.health'),
      ]);

      setProviders(Array.isArray(providersData) ? (providersData as ProviderInfo[]) : []);
      setModels(Array.isArray(modelsData) ? (modelsData as ModelInfo[]) : []);
      setRouting(Array.isArray(routingData) ? (routingData as RoutingEntry[]) : []);
      setHealth((healthData || {}) as Record<string, ProviderHealth>);

      setLastRefresh(new Date());
    } catch (err) {
      setError(
        err instanceof Error
          ? `Providers integration failed: ${err.message}`
          : 'Providers integration failed'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      await callMCPTool('providers.refresh');

      // Re-fetch all data
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error
          ? `Provider refresh failed: ${err.message}`
          : 'Provider refresh failed'
      );
    } finally {
      setIsLoading(false);
    }
  }, [fetchAll]);

  useEffect(() => {
    fetchAll();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return {
    providers,
    models,
    routing,
    health,
    isLoading,
    error,
    refresh,
    lastRefresh,
  };
}
