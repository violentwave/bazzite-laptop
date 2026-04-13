"use client";

import React, { useState } from 'react';
import { ModelInfo, ProviderInfo, TaskType, TASK_TYPE_LABELS } from '@/types/providers';

interface ModelCatalogPanelProps {
  models: ModelInfo[];
  providers: ProviderInfo[];
}

export function ModelCatalogPanel({ models, providers }: ModelCatalogPanelProps) {
  const [filterTaskType, setFilterTaskType] = useState<TaskType | 'all'>('all');
  const [filterProvider, setFilterProvider] = useState<string>('all');

  const filteredModels = models.filter((model) => {
    if (filterTaskType !== 'all' && !model.task_types.includes(filterTaskType)) {
      return false;
    }
    if (filterProvider !== 'all' && model.provider !== filterProvider) {
      return false;
    }
    return true;
  });

  // Group by provider
  const groupedModels = filteredModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  }, {} as Record<string, ModelInfo[]>);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div
        className="flex gap-4 p-4 rounded-xl border"
        style={{
          background: 'var(--base-02)',
          borderColor: 'var(--base-04)',
        }}
      >
        <div className="flex-1">
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            Task Type
          </label>
          <select
            value={filterTaskType}
            onChange={(e) => setFilterTaskType(e.target.value as TaskType | 'all')}
            className="w-full px-3 py-2 rounded-lg outline-none text-sm"
            style={{
              background: 'var(--base-03)',
              border: '1px solid var(--base-04)',
              color: 'var(--text-primary)',
            }}
          >
            <option value="all">All Task Types</option>
            {Object.entries(TASK_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1">
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            Provider
          </label>
          <select
            value={filterProvider}
            onChange={(e) => setFilterProvider(e.target.value)}
            className="w-full px-3 py-2 rounded-lg outline-none text-sm"
            style={{
              background: 'var(--base-03)',
              border: '1px solid var(--base-04)',
              color: 'var(--text-primary)',
            }}
          >
            <option value="all">All Providers</option>
            {providers
              .filter((p) => p.is_configured)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
          </select>
        </div>
      </div>

      {/* Model Count */}
      <div
        className="text-sm"
        style={{ color: 'var(--text-secondary)' }}
      >
        Showing {filteredModels.length} of {models.length} models
      </div>

      {/* Model Grid */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(groupedModels).map(([providerId, providerModels]) => {
          const provider = providers.find((p) => p.id === providerId);
          if (!provider) return null;

          return (
            <div
              key={providerId}
              className="rounded-xl border"
              style={{
                background: 'var(--base-02)',
                borderColor: 'var(--base-04)',
              }}
            >
              <div
                className="px-4 py-3 border-b flex items-center justify-between"
                style={{ borderColor: 'var(--base-04)' }}
              >
                <div>
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
                    {providerModels.length} models
                  </div>
                </div>
                <StatusBadge status={provider.status} />
              </div>

              <div className="divide-y" style={{ borderColor: 'var(--base-04)' }}>
                {providerModels.map((model) => (
                  <div
                    key={model.id}
                    className="px-4 py-3 hover:bg-[var(--base-03)] transition-colors"
                  >
                    <div
                      className="font-medium text-sm"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {model.name}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {model.task_types.map((taskType) => (
                        <span
                          key={taskType}
                          className="px-2 py-0.5 rounded text-xs"
                          style={{
                            background: 'var(--base-03)',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {TASK_TYPE_LABELS[taskType as TaskType] || taskType}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {filteredModels.length === 0 && (
        <div
          className="p-8 text-center rounded-xl border"
          style={{
            background: 'var(--base-02)',
            borderColor: 'var(--base-04)',
            color: 'var(--text-secondary)',
          }}
        >
          No models match the selected filters.
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    healthy: 'var(--success)',
    degraded: 'var(--warning)',
    blocked: 'var(--danger)',
    unavailable: 'var(--danger)',
    not_configured: 'var(--text-tertiary)',
  };

  return (
    <span
      className="w-2 h-2 rounded-full"
      style={{ background: colors[status] || colors.not_configured }}
    />
  );
}
