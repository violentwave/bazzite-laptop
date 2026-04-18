"use client";

import { useState, useEffect } from 'react';
import { ModelInfo, ProviderInfo, TaskType, TASK_TYPE_LABELS, TASK_TYPE_DESCRIPTIONS } from '@/types/providers';

const STORAGE_KEY = 'bazzite-chat-profile';

const DEFAULT_PROFILE: TaskType = 'fast';

interface ChatProfileSelectorProps {
  mode?: TaskType;
  onModeChange?: (mode: TaskType) => void;
  provider?: string;
  onProviderChange?: (provider: string) => void;
  model?: string;
  onModelChange?: (model: string) => void;
  providers: ProviderInfo[];
  models: ModelInfo[];
  isLoading?: boolean;
}

export function ChatProfileSelector({ 
  mode = DEFAULT_PROFILE,
  onModeChange,
  provider = '', 
  onProviderChange, 
  model = '', 
  onModelChange,
  providers,
  models,
  isLoading = false,
}: ChatProfileSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [providerOpen, setProviderOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  
  const taskTypes: TaskType[] = ['fast', 'reason', 'batch', 'code', 'embed'];

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && taskTypes.includes(stored as TaskType)) {
      onModeChange?.(stored as TaskType);
    }
  }, [onModeChange]);

  const handleSelect = (profile: TaskType) => {
    localStorage.setItem(STORAGE_KEY, profile);
    onModeChange?.(profile);
    setIsOpen(false);
  };

  const handleProviderSelect = (p: string) => {
    onProviderChange?.(p);
    onModelChange?.(''); // Reset model when provider changes
    setProviderOpen(false);
  };

  const handleModelSelect = (m: string) => {
    onModelChange?.(m);
    setModelOpen(false);
  };

  const availableModels = provider 
    ? models.filter(m => m.provider === provider)
    : models;

  const selectedProvider = providers.find(p => p.id === provider);
  const selectedModel = availableModels.find((m) => m.id === model);

  return (
    <div className="flex items-center gap-2">
      {/* Profile/Mode Selector */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
          style={{
            background: 'var(--base-03)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--base-04)',
          }}
          title="Select chat mode"
        >
          <ProfileIcon />
          <span>{TASK_TYPE_LABELS[mode]}</span>
          <ChevronIcon className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div
            className="absolute top-full mt-1 left-0 z-50 min-w-[200px] rounded-lg shadow-lg overflow-hidden"
            style={{
              background: 'var(--base-02)',
              border: '1px solid var(--base-04)',
            }}
          >
            {taskTypes.map((type) => (
              <button
                key={type}
                onClick={() => handleSelect(type)}
                className="w-full px-4 py-2 text-left text-sm transition-colors flex items-start gap-2"
                style={{
                  background: mode === type ? 'var(--base-03)' : 'transparent',
                  color: 'var(--text-primary)',
                }}
              >
                <div className="flex-1">
                  <div className="font-medium">{TASK_TYPE_LABELS[type]}</div>
                  <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    {TASK_TYPE_DESCRIPTIONS[type]}
                  </div>
                </div>
                {mode === type && <CheckIcon />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Provider Selector */}
      <div className="relative">
        <button
          onClick={() => setProviderOpen(!providerOpen)}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
          style={{
            background: 'var(--base-03)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--base-04)',
          }}
          title="Select provider"
        >
          <ProviderIcon />
          <span>{selectedProvider?.name || 'Provider'}</span>
          <ChevronIcon className={`transition-transform ${providerOpen ? 'rotate-180' : ''}`} />
        </button>

        {providerOpen && (
          <div
            className="absolute top-full mt-1 left-0 z-50 min-w-[180px] rounded-lg shadow-lg overflow-hidden"
            style={{
              background: 'var(--base-02)',
              border: '1px solid var(--base-04)',
            }}
          >
            {providers.length === 0 ? (
              <div className="px-4 py-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                {isLoading ? 'Loading...' : 'No providers'}
              </div>
            ) : (
              providers.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleProviderSelect(p.id)}
                  className="w-full px-4 py-2 text-left text-sm transition-colors flex items-center gap-2"
                  style={{
                    background: provider === p.id ? 'var(--base-03)' : 'transparent',
                    color: 'var(--text-primary)',
                  }}
                >
                  <span className={`w-2 h-2 rounded-full ${
                    p.status === 'healthy' ? 'bg-success' :
                    p.status === 'degraded' ? 'bg-warning' : 'bg-danger'
                  }`} />
                  <span className="flex-1">{p.name}</span>
                  {provider === p.id && <CheckIcon />}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Model Selector */}
      <div className="relative">
        <button
          onClick={() => setModelOpen(!modelOpen)}
          disabled={isLoading || !provider}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors disabled:opacity-50"
          style={{
            background: 'var(--base-03)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--base-04)',
          }}
          title="Select model"
        >
          <ModelIcon />
          <span>{selectedModel?.name || model || 'Model'}</span>
          <ChevronIcon className={`transition-transform ${modelOpen ? 'rotate-180' : ''}`} />
        </button>

        {modelOpen && (
          <div
            className="absolute top-full mt-1 left-0 z-50 min-w-[180px] rounded-lg shadow-lg overflow-hidden max-h-60 overflow-y-auto"
            style={{
              background: 'var(--base-02)',
              border: '1px solid var(--base-04)',
            }}
          >
            {availableModels.length === 0 ? (
              <div className="px-4 py-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                {isLoading ? 'Loading...' : 'Select a provider first'}
              </div>
            ) : (
              availableModels.map((m) => (
                <button
                  key={m.id}
                  onClick={() => handleModelSelect(m.id)}
                  className="w-full px-4 py-2 text-left text-sm transition-colors flex items-center gap-2"
                  style={{
                    background: model === m.id ? 'var(--base-03)' : 'transparent',
                    color: 'var(--text-primary)',
                  }}
                >
                  <span className="flex-1">{m.name}</span>
                  {model === m.id && <CheckIcon />}
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ProfileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a4 4 0 0 1 4 4c0 1.1-.9 2-2 2s-2-.9-2-2a4 4 0 0 1 0-8" />
      <path d="M12 8v8" />
      <path d="M8 12H4" />
      <path d="M20 12h-4" />
    </svg>
  );
}

function ProviderIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

function ModelIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect width="18" height="10" x="3" y="11" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--accent-primary)' }}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
