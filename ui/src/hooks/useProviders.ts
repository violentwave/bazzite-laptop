"use client";

import { useState, useEffect, useCallback } from 'react';
import { ProviderInfo, ModelInfo, RoutingEntry, ProviderHealth } from '@/types/providers';
import { callMCPTool } from '@/lib/mcp-client';

interface ProviderCounts {
  total: number;
  configured: number;
  healthy: number;
  degraded: number;
  blocked: number;
}

interface ProvidersResponse {
  success?: boolean;
  providers?: ProviderInfo[];
  counts?: ProviderCounts;
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface ModelsResponse {
  success?: boolean;
  models?: ModelInfo[];
  count?: number;
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface RoutingResponse {
  success?: boolean;
  routing?: RoutingEntry[];
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface HealthResponse {
  success?: boolean;
  health?: Record<string, ProviderHealth>;
  summary?: {
    auth_broken_count: number;
    auth_broken_providers: string[];
    cooldown_count: number;
    cooldown_providers: string[];
  };
  error_code?: string;
  error?: string;
  operator_action?: string;
}

interface UseProvidersReturn {
  providers: ProviderInfo[];
  models: ModelInfo[];
  routing: RoutingEntry[];
  health: Record<string, ProviderHealth>;
  counts: ProviderCounts | null;
  healthSummary: HealthResponse['summary'] | null;
  isLoading: boolean;
  error: string | null;
  errorCode: string | null;
  operatorAction: string | null;
  refresh: () => Promise<void>;
  lastRefresh: Date | null;
}

function formatProviderError(response: ProvidersResponse | ModelsResponse | RoutingResponse | HealthResponse): { message: string; code: string; action: string } {
  const code = response.error_code || 'unknown_error';
  const action = response.operator_action || 'Check MCP bridge and provider service health';

  switch (code) {
    case 'config_unavailable':
      return {
        message: response.error || 'LiteLLM configuration file not found',
        code,
        action: 'Create configs/litellm-config.yaml with provider routing configuration',
      };
    case 'provider_discovery_failed':
      return {
        message: response.error || 'Failed to discover providers',
        code,
        action,
      };
    case 'model_catalog_failed':
      return {
        message: response.error || 'Failed to get model catalog',
        code,
        action,
      };
    case 'routing_config_failed':
      return {
        message: response.error || 'Failed to get routing configuration',
        code,
        action: 'Check LiteLLM configuration file format',
      };
    case 'health_data_failed':
      return {
        message: response.error || 'Failed to get provider health data',
        code,
        action,
      };
    default:
      return {
        message: response.error || 'Provider service error',
        code,
        action,
      };
  }
}

export function useProviders(): UseProvidersReturn {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [routing, setRouting] = useState<RoutingEntry[]>([]);
  const [health, setHealth] = useState<Record<string, ProviderHealth>>({});
  const [counts, setCounts] = useState<ProviderCounts | null>(null);
  const [healthSummary, setHealthSummary] = useState<HealthResponse['summary'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [operatorAction, setOperatorAction] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setErrorCode(null);
    setOperatorAction(null);

    try {
      const [providersData, modelsData, routingData, healthData] = await Promise.all([
        callMCPTool('providers.discover'),
        callMCPTool('providers.models'),
        callMCPTool('providers.routing'),
        callMCPTool('providers.health'),
      ]);

      // Handle providers response
      const providersResp = providersData as ProvidersResponse;
      if (providersResp.success === false) {
        const err = formatProviderError(providersResp);
        setError(err.message);
        setErrorCode(err.code);
        setOperatorAction(err.action);
        setProviders([]);
        setCounts(null);
      } else {
        setProviders(providersResp.providers || []);
        setCounts(providersResp.counts || null);
      }

      // Handle models response
      const modelsResp = modelsData as ModelsResponse;
      if (modelsResp.success === false) {
        // Don't overwrite error if providers already failed
        if (!error) {
          const err = formatProviderError(modelsResp);
          setError(err.message);
          setErrorCode(err.code);
          setOperatorAction(err.action);
        }
        setModels([]);
      } else {
        setModels(modelsResp.models || []);
      }

      // Handle routing response
      const routingResp = routingData as RoutingResponse;
      if (routingResp.success === false) {
        if (!error) {
          const err = formatProviderError(routingResp);
          setError(err.message);
          setErrorCode(err.code);
          setOperatorAction(err.action);
        }
        setRouting([]);
      } else {
        setRouting(routingResp.routing || []);
      }

      // Handle health response
      const healthResp = healthData as HealthResponse;
      if (healthResp.success === false) {
        if (!error) {
          const err = formatProviderError(healthResp);
          setError(err.message);
          setErrorCode(err.code);
          setOperatorAction(err.action);
        }
        setHealth({});
        setHealthSummary(null);
      } else {
        setHealth(healthResp.health || {});
        setHealthSummary(healthResp.summary || null);
      }

      setLastRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Provider service unavailable';
      setError(`Cannot connect to provider service: ${message}`);
      setErrorCode('connection_failed');
      setOperatorAction('Ensure MCP bridge is running on port 8766');
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
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Provider refresh failed: ${message}`);
      setErrorCode('refresh_failed');
      setOperatorAction('Check MCP bridge connection and retry');
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
    counts,
    healthSummary,
    isLoading,
    error,
    errorCode,
    operatorAction,
    refresh,
    lastRefresh,
  };
}
