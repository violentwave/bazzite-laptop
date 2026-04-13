"use client";

import React, { useState } from 'react';
import { useProviders } from '@/hooks/useProviders';
import { ProviderHealthPanel } from './ProviderHealthPanel';
import { ModelCatalogPanel } from './ModelCatalogPanel';
import { RoutingConsole } from './RoutingConsole';

type Tab = 'health' | 'models' | 'routing';

export function ProvidersContainer() {
  const [activeTab, setActiveTab] = useState<Tab>('health');
  const { providers, models, routing, health, isLoading, error, refresh, lastRefresh } = useProviders();

  const configuredCount = providers.filter(p => p.is_configured).length;
  const healthyCount = providers.filter(p => p.is_healthy).length;

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
          count={5}
          isActive={activeTab === 'routing'}
          onClick={() => setActiveTab('routing')}
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {error && (
          <div
            className="mb-4 p-4 rounded-lg"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid var(--danger)',
              color: 'var(--danger)',
            }}
          >
            {error}
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
