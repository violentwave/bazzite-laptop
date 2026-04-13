"use client";

import { useState, useEffect, useCallback } from 'react';
import { ProviderInfo, ModelInfo, RoutingEntry, ProviderHealth } from '@/types/providers';

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
      // Fetch providers
      const providersRes = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'providers.discover' }),
      });
      const providersData = await providersRes.json();
      setProviders(providersData);

      // Fetch models
      const modelsRes = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'providers.models' }),
      });
      const modelsData = await modelsRes.json();
      setModels(modelsData);

      // Fetch routing
      const routingRes = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'providers.routing' }),
      });
      const routingData = await routingRes.json();
      setRouting(routingData);

      // Fetch health
      const healthRes = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'providers.health' }),
      });
      const healthData = await healthRes.json();
      setHealth(healthData);

      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch provider data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      // Trigger refresh
      await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'providers.refresh' }),
      });

      // Re-fetch all data
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh providers');
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
