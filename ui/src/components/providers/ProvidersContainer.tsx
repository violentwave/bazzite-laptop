"use client";

import React, { useState } from 'react';
import { useProviders } from '@/hooks/useProviders';
import { ProviderHealthPanel } from './ProviderHealthPanel';
import { ModelCatalogPanel } from './ModelCatalogPanel';
import { RoutingConsole } from './RoutingConsole';
import { AddProviderPanel } from './AddProviderPanel';

type Tab = 'health' | 'models' | 'routing' | 'add';

function getErrorSeverity(errorCode: string | null): 'error' | 'warning' | 'info' {
  if (!errorCode) return 'error';
  if (errorCode === 'config_unavailable') return 'warning';
  if (errorCode === 'connection_failed') return 'error';
  return 'warning';
}

function ErrorState({
  error,
  errorCode,
  operatorAction,
  onRetry,
}: {
  error: string;
  errorCode: string | null;
  operatorAction: string | null;
  onRetry: () => void;
}) {
  const severity = getErrorSeverity(errorCode);

  const colors = {
    error: {
      border: 'var(--danger)',
      bg: 'rgba(239, 68, 68, 0.1)',
      icon: 'var(--danger)',
    },
    warning: {
      border: 'var(--warning)',
      bg: 'rgba(245, 158, 11, 0.1)',
      icon: 'var(--warning)',
    },
    info: {
      border: 'var(--info)',
      bg: 'rgba(59, 130, 246, 0.1)',
      icon: 'var(--info)',
    },
  };

  const c = colors[severity];

  return (
    <div
      className="max-w-lg mx-auto p-6 rounded-xl border"
      style={{
        background: c.bg,
        borderColor: c.border,
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke={c.icon}
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <h3 className="font-medium" style={{ color: 'var(--text-primary)' }}>
          {errorCode === 'config_unavailable'
            ? 'Configuration Required'
            : errorCode === 'connection_failed'
            ? 'Connection Failed'
            : 'Provider Service Issue'}
        </h3>
      </div>

      <p className="mb-2" style={{ color: 'var(--text-secondary)' }}>
        {error}
      </p>

      {operatorAction && (
        <div
          className="mb-4 p-3 rounded-lg text-sm"
          style={{
            background: 'var(--base-01)',
            color: 'var(--text-secondary)',
          }}
        >
          <strong>Action needed:</strong> {operatorAction}
        </div>
      )}

      <button
        onClick={onRetry}
        className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        style={{
          background: 'var(--accent-primary)',
          color: 'white',
        }}
      >
        Retry
      </button>
    </div>
  );
}

export function ProvidersContainer() {
  const [activeTab, setActiveTab] = useState<Tab>('health');
  const {
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
  } = useProviders();

  const configuredCount = counts?.configured ?? providers.filter(p => p.is_configured).length;
  const healthyCount = counts?.healthy ?? providers.filter(p => p.is_healthy).length;
  const degradedCount = counts?.degraded ?? providers.filter(p => p.status === 'degraded').length;
  const blockedCount = counts?.blocked ?? providers.filter(p => p.status === 'blocked').length;

  // Check if we have partial data (some providers loaded but errors occurred)
  const hasPartialData = providers.length > 0 && error;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b"
        style={{
          borderColor: 'var(--base-04)',
          background: 'var(--base-01)',
        }}
      >
        <div>
          <h1
            className="text-lg font-semibold"
            style={{ color: 'var(--text-primary)' }}
          >
            Providers & Models
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
            {configuredCount} configured · {healthyCount} healthy
            {degradedCount > 0 && (
              <span style={{ color: 'var(--warning)' }}> · {degradedCount} degraded</span>
            )}
            {blockedCount > 0 && (
              <span style={{ color: 'var(--danger)' }}> · {blockedCount} blocked</span>
            )}
            {lastRefresh && (
              <span className="ml-2">
                · Updated {lastRefresh.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>

        <button
          onClick={refresh}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          style={{
            background: 'var(--accent-primary)',
            color: 'white',
          }}
        >
          {isLoading ? (
            <>
              <SpinnerIcon />
              Refreshing...
            </>
          ) : (
            <>
              <RefreshIcon />
              Refresh
            </>
          )}
        </button>
      </div>

      {/* Auth Broken Warning */}
      {healthSummary && healthSummary.auth_broken_count > 0 && (
        <div
          className="px-6 py-3 border-b"
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            borderColor: 'var(--danger)',
          }}
        >
          <div className="flex items-center gap-2">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--danger)"
              strokeWidth="2"
            >
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y2="17" y1="17" x2="12.01" />
            </svg>
            <span style={{ color: 'var(--danger)' }}>
              <strong>Authentication failed</strong> for {healthSummary.auth_broken_count} provider
              {healthSummary.auth_broken_count !== 1 ? 's' : ''}: {healthSummary.auth_broken_providers.join(', ')}.{' '}
              Open the Settings panel to update API keys.
            </span>
          </div>
        </div>
      )}

      {/* Cooldown Warning */}
      {healthSummary && healthSummary.cooldown_count > 0 && (
        <div
          className="px-6 py-3 border-b"
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            borderColor: 'var(--warning)',
          }}
        >
          <div className="flex items-center gap-2">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--warning)"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span style={{ color: 'var(--warning)' }}>
              <strong>Cooldown active</strong> for {healthSummary.cooldown_count} provider
              {healthSummary.cooldown_count !== 1 ? 's' : ''}: {healthSummary.cooldown_providers.join(', ')}.{' '}
              Auto-recovery in progress.
            </span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div
        className="flex border-b"
        style={{ borderColor: 'var(--base-04)' }}
      >
        <TabButton
          label="Health"
          count={providers.length}
          isActive={activeTab === 'health'}
          onClick={() => setActiveTab('health')}
        />
        <TabButton
          label="Models"
          count={models.length}
          isActive={activeTab === 'models'}
          onClick={() => setActiveTab('models')}
        />
        <TabButton
          label="Routing"
          count={routing.length}
          isActive={activeTab === 'routing'}
          onClick={() => setActiveTab('routing')}
        />
        <TabButton
          label="Add"
          count={0}
          isActive={activeTab === 'add'}
          onClick={() => setActiveTab('add')}
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {/* Error State - No Data */}
        {error && !hasPartialData && (
          <ErrorState
            error={error}
            errorCode={errorCode}
            operatorAction={operatorAction}
            onRetry={refresh}
          />
        )}

        {/* Partial Data Warning */}
        {hasPartialData && (
          <div
            className="mb-4 p-4 rounded-lg"
            style={{
              background: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid var(--warning)',
              color: 'var(--warning)',
            }}
          >
            <div className="flex items-center gap-2">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y2="17" y1="17" x2="12.01" />
              </svg>
              <span>{error}</span>
            </div>
            {operatorAction && (
              <p className="mt-2 text-sm">{operatorAction}</p>
            )}
          </div>
        )}

        {isLoading && !providers.length ? (
          <LoadingState />
        ) : (
          <>
            {activeTab === 'health' && (
              <ProviderHealthPanel providers={providers} health={health} />
            )}
            {activeTab === 'models' && (
              <ModelCatalogPanel models={models} providers={providers} />
            )}
            {activeTab === 'routing' && (
              <RoutingConsole routing={routing} providers={providers} />
            )}
            {activeTab === 'add' && (
              <AddProviderPanel providers={providers} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function TabButton({
  label,
  count,
  isActive,
  onClick,
}: {
  label: string;
  count: number;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="px-6 py-3 text-sm font-medium transition-colors relative"
      style={{
        color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
        borderBottom: isActive ? '2px solid var(--accent-primary)' : 'none',
      }}
    >
      {label}
      <span
        className="ml-2 px-2 py-0.5 rounded-full text-xs"
        style={{
          background: isActive ? 'var(--accent-primary)' : 'var(--base-03)',
          color: isActive ? 'white' : 'var(--text-tertiary)',
        }}
      >
        {count}
      </span>
    </button>
  );
}

function LoadingState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div
          className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-4"
          style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }}
        />
        <p style={{ color: 'var(--text-secondary)' }}>Loading providers...</p>
      </div>
    </div>
  );
}

function SpinnerIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="animate-spin"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
      <path d="M16 16h5v5" />
    </svg>
  );
}
