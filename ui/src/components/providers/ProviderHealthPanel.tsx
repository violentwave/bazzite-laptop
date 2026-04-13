"use client";

import React from 'react';
import { ProviderInfo, ProviderHealth } from '@/types/providers';

interface ProviderHealthPanelProps {
  providers: ProviderInfo[];
  health: Record<string, ProviderHealth>;
}

export function ProviderHealthPanel({ providers, health }: ProviderHealthPanelProps) {
  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <SummaryCard
          label="Configured"
          value={providers.filter(p => p.is_configured).length}
          total={providers.length}
          color="var(--accent-primary)"
        />
        <SummaryCard
          label="Healthy"
          value={providers.filter(p => p.is_healthy).length}
          total={providers.length}
          color="var(--success)"
        />
        <SummaryCard
          label="Degraded"
          value={providers.filter(p => p.status === 'degraded').length}
          total={providers.length}
          color="var(--warning)"
        />
        <SummaryCard
          label="Blocked"
          value={providers.filter(p => p.status === 'blocked' || p.status === 'unavailable').length}
          total={providers.length}
          color="var(--danger)"
        />
      </div>

      {/* Provider List */}
      <div
        className="rounded-xl border"
        style={{
          background: 'var(--base-02)',
          borderColor: 'var(--base-04)',
        }}
      >
        <div
          className="px-4 py-3 border-b grid grid-cols-12 gap-4 text-sm font-medium"
          style={{
            borderColor: 'var(--base-04)',
            color: 'var(--text-secondary)',
          }}
        >
          <div className="col-span-3">Provider</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2">Health Score</div>
          <div className="col-span-2">Models</div>
          <div className="col-span-3">Last Error</div>
        </div>

        <div className="divide-y" style={{ borderColor: 'var(--base-04)' }}>
          {providers.map((provider) => (
            <ProviderRow
              key={provider.id}
              provider={provider}
              health={health[provider.id]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  return (
    <div
      className="p-4 rounded-xl border"
      style={{
        background: 'var(--base-02)',
        borderColor: 'var(--base-04)',
      }}
    >
      <div
        className="text-2xl font-bold mb-1"
        style={{ color }}
      >
        {value}
        <span
          className="text-sm font-normal ml-1"
          style={{ color: 'var(--text-tertiary)' }}
        >
          / {total}
        </span>
      </div>
      <div
        className="text-sm"
        style={{ color: 'var(--text-secondary)' }}
      >
        {label}
      </div>
    </div>
  );
}

function ProviderRow({
  provider,
  health,
}: {
  provider: ProviderInfo;
  health: ProviderHealth | undefined;
}) {
  const statusColors: Record<string, string> = {
    healthy: 'var(--success)',
    degraded: 'var(--warning)',
    blocked: 'var(--danger)',
    unavailable: 'var(--danger)',
    not_configured: 'var(--text-tertiary)',
  };

  const statusLabels: Record<string, string> = {
    healthy: 'Healthy',
    degraded: 'Degraded',
    blocked: 'Blocked',
    unavailable: 'Unavailable',
    not_configured: 'Not Configured',
  };

  return (
    <div className="px-4 py-3 grid grid-cols-12 gap-4 items-center hover:bg-[var(--base-03)] transition-colors">
      <div className="col-span-3">
        <div
          className="font-medium"
          style={{ color: 'var(--text-primary)' }}
        >
          {provider.name}
        </div>
        <div
          className="text-xs"
          style={{ color: 'var(--text-tertiary)' }}
        >
          {provider.id}
          {provider.is_local && ' · Local'}
        </div>
      </div>

      <div className="col-span-2">
        <span
          className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium"
          style={{
            background: `${statusColors[provider.status]}20`,
            color: statusColors[provider.status],
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: statusColors[provider.status] }}
          />
          {statusLabels[provider.status]}
        </span>
      </div>

      <div className="col-span-2">
        {provider.is_configured ? (
          <div className="flex items-center gap-2">
            <div
              className="flex-1 h-2 rounded-full overflow-hidden"
              style={{ background: 'var(--base-04)' }}
            >
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${(health?.score || provider.health_score) * 100}%`,
                  background: (health?.score || provider.health_score) > 0.7
                    ? 'var(--success)'
                    : (health?.score || provider.health_score) > 0.4
                    ? 'var(--warning)'
                    : 'var(--danger)',
                }}
              />
            </div>
            <span
              className="text-xs tabular-nums"
              style={{ color: 'var(--text-secondary)' }}
            >
              {((health?.score || provider.health_score) * 100).toFixed(0)}%
            </span>
          </div>
        ) : (
          <span
            className="text-xs"
            style={{ color: 'var(--text-tertiary)' }}
          >
            —
          </span>
        )}
      </div>

      <div className="col-span-2">
        <span
          className="text-sm"
          style={{ color: 'var(--text-secondary)' }}
        >
          {provider.models.length} models
        </span>
      </div>

      <div className="col-span-3">
        {provider.last_error ? (
          <div
            className="text-xs truncate"
            style={{ color: 'var(--danger)' }}
            title={provider.last_error}
          >
            {provider.last_error}
          </div>
        ) : health?.consecutive_failures ? (
          <div
            className="text-xs"
            style={{ color: 'var(--warning)' }}
          >
            {health.consecutive_failures} consecutive failures
          </div>
        ) : (
          <span
            className="text-xs"
            style={{ color: 'var(--text-tertiary)' }}
          >
            No issues
          </span>
        )}
      </div>
    </div>
  );
}
