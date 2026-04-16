"use client";

import React from 'react';
import { RoutingEntry, ProviderInfo, TASK_TYPE_LABELS, TASK_TYPE_DESCRIPTIONS, TaskType } from '@/types/providers';

interface RoutingConsoleProps {
  routing: RoutingEntry[];
  providers: ProviderInfo[];
}

export function RoutingConsole({ routing, providers }: RoutingConsoleProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div
        className="p-4 rounded-xl border"
        style={{
          background: 'var(--base-02)',
          borderColor: 'var(--base-04)',
        }}
      >
        <h3
          className="font-medium mb-2"
          style={{ color: 'var(--text-primary)' }}
        >
          Task Type Routing
        </h3>
        <p
          className="text-sm"
          style={{ color: 'var(--text-secondary)' }}
        >
          Each task type has a primary provider and fallback chain. The router selects
          the best available provider based on health scores and cooldown status.
        </p>
        <p
          className="text-xs mt-2"
          style={{ color: 'var(--text-tertiary)' }}
        >
          Routing is controlled by backend config (litellm-config.yaml). Runtime persistence is deferred to P115/P116.
        </p>
      </div>

      {/* Routing Cards */}
      <div className="space-y-4">
        {routing.map((entry) => (
          <RoutingCard
            key={entry.task_type}
            entry={entry}
            providers={providers}
          />
        ))}
      </div>
    </div>
  );
}

function RoutingCard({
  entry,
  providers,
}: {
  entry: RoutingEntry;
  providers: ProviderInfo[];
}) {
  const primaryProvider = providers.find((p) => p.id === entry.primary_provider);
  const fallbackProviders = entry.fallback_chain
    .map((id) => providers.find((p) => p.id === id))
    .filter(Boolean);

  const isHealthy = entry.health_state === 'mixed' || entry.health_state === 'healthy';
  const isBlocked = entry.health_state === 'all-blocked' || entry.health_state === 'all-cooldown';

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        background: 'var(--base-02)',
        borderColor: isBlocked ? 'var(--danger)' : isHealthy ? 'var(--base-04)' : 'var(--warning)',
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 border-b flex items-center justify-between"
        style={{ borderColor: 'var(--base-04)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--base-03)' }}
          >
            <TaskTypeIcon taskType={entry.task_type as TaskType} />
          </div>
          <div>
            <div
              className="font-medium"
              style={{ color: 'var(--text-primary)' }}
            >
              {entry.task_label}
            </div>
            <div
              className="text-xs"
              style={{ color: 'var(--text-tertiary)' }}
            >
              {TASK_TYPE_DESCRIPTIONS[entry.task_type as TaskType]}
            </div>
          </div>
        </div>

        <HealthIndicator state={entry.health_state} />
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Primary Provider */}
        <div>
          <div
            className="text-xs font-medium mb-2 uppercase tracking-wide"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Primary Provider
          </div>
          {primaryProvider ? (
            <ProviderPill provider={primaryProvider} isPrimary />
          ) : (
            <div
              className="text-sm"
              style={{ color: 'var(--danger)' }}
            >
              No configured provider available
            </div>
          )}
        </div>

        {/* Fallback Chain */}
        {fallbackProviders.length > 0 && (
          <div>
            <div
              className="text-xs font-medium mb-2 uppercase tracking-wide"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Fallback Chain
            </div>
            <div className="flex flex-wrap gap-2">
              {fallbackProviders.map((provider, index) => (
                <div key={provider!.id} className="flex items-center gap-2">
                  <ProviderPill provider={provider!} />
                  {index < fallbackProviders.length - 1 && (
                    <span style={{ color: 'var(--text-tertiary)' }}>→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Eligible Models */}
        {entry.eligible_models.length > 0 && (
          <div>
            <div
              className="text-xs font-medium mb-2 uppercase tracking-wide"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Eligible Models
            </div>
            <div className="flex flex-wrap gap-2">
              {entry.eligible_models.map((model) => (
                <span
                  key={model.id}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: 'var(--base-03)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {model.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Caveats */}
        {entry.caveats && (
          <div
            className="p-3 rounded-lg text-sm flex items-start gap-2"
            style={{
              background: 'rgba(245, 158, 11, 0.1)',
              color: 'var(--warning)',
            }}
          >
            <WarningIcon />
            {entry.caveats}
          </div>
        )}
      </div>
    </div>
  );
}

function ProviderPill({
  provider,
  isPrimary = false,
}: {
  provider: ProviderInfo;
  isPrimary?: boolean;
}) {
  const statusColors: Record<string, string> = {
    healthy: 'var(--success)',
    degraded: 'var(--warning)',
    blocked: 'var(--danger)',
    unavailable: 'var(--danger)',
    not_configured: 'var(--text-tertiary)',
  };

  return (
    <div
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm"
      style={{
        background: isPrimary ? 'var(--base-03)' : 'var(--base-03)',
        border: isPrimary ? '1px solid var(--accent-primary)' : 'none',
      }}
    >
      <span
        className="w-2 h-2 rounded-full"
        style={{ background: statusColors[provider.status] || statusColors.not_configured }}
      />
      <span style={{ color: 'var(--text-primary)' }}>
        {provider.name}
      </span>
      {isPrimary && (
        <span
          className="text-xs px-1.5 py-0.5 rounded"
          style={{
            background: 'var(--accent-primary)',
            color: 'white',
          }}
        >
          Primary
        </span>
      )}
    </div>
  );
}

function HealthIndicator({ state }: { state: string }) {
  const config: Record<string, { color: string; label: string }> = {
    healthy: { color: 'var(--success)', label: 'Healthy' },
    mixed: { color: 'var(--warning)', label: 'Mixed' },
    'all-blocked': { color: 'var(--danger)', label: 'Blocked' },
    'all-cooldown': { color: 'var(--danger)', label: 'Cooldown' },
    'no-providers-configured': { color: 'var(--text-tertiary)', label: 'Not Configured' },
  };

  const { color, label } = config[state] || config['no-providers-configured'];

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
      style={{
        background: `${color}20`,
        color,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label}
    </div>
  );
}

function TaskTypeIcon({ taskType }: { taskType: TaskType }) {
  const icons: Record<TaskType, React.ReactNode> = {
    fast: <ZapIcon />,
    reason: <BrainIcon />,
    batch: <LayersIcon />,
    code: <CodeIcon />,
    embed: <VectorIcon />,
  };

  return (
    <span style={{ color: 'var(--accent-primary)' }}>
      {icons[taskType] || <ZapIcon />}
    </span>
  );
}

function ZapIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

function BrainIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  );
}

function LayersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function VectorIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v4" />
      <path d="M12 18v4" />
      <path d="M4.93 4.93l2.83 2.83" />
      <path d="M16.24 16.24l2.83 2.83" />
      <path d="M2 12h4" />
      <path d="M18 12h4" />
      <path d="M4.93 19.07l2.83-2.83" />
      <path d="M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" x2="12" y1="9" y2="13" />
      <line x1="12" x2="12.01" y1="17" y2="17" />
    </svg>
  );
}
