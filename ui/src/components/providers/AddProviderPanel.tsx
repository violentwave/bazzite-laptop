"use client";

import React, { useState } from 'react';
import { ProviderInfo } from '@/types/providers';

interface AddProviderPanelProps {
  providers: ProviderInfo[];
}

const KNOWN_PROVIDERS = [
  { id: 'openai', name: 'OpenAI', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  { id: 'anthropic', name: 'Anthropic', apiKeyEnv: 'ANTHROPIC_API_KEY', baseUrl: 'https://api.anthropic.com' },
  { id: 'groq', name: 'Groq', apiKeyEnv: 'GROQ_API_KEY', baseUrl: 'https://api.groq.com/openai/v1' },
  { id: 'mistral', name: 'Mistral', apiKeyEnv: 'MISTRAL_API_KEY', baseUrl: 'https://api.mistral.ai/v1' },
  { id: 'gemini', name: 'Google Gemini', apiKeyEnv: 'GEMINI_API_KEY', baseUrl: 'https://generativelanguage.googleapis.com/v1' },
  { id: 'openrouter', name: 'OpenRouter', apiKeyEnv: 'OPENROUTER_API_KEY', baseUrl: 'https://openrouter.ai/api/v1' },
  { id: 'cerebras', name: 'Cerebras', apiKeyEnv: 'CEREBRAS_API_KEY', baseUrl: 'https://api.cerebras.ai' },
  { id: 'zhipuai', name: 'Zhipuai', apiKeyEnv: 'ZAI_API_KEY', baseUrl: 'https://api.z.ai/api/paas/v1' },
  { id: 'ollama', name: 'Ollama (Local)', apiKeyEnv: null, baseUrl: 'http://localhost:11434' },
];

export function AddProviderPanel({ providers }: AddProviderPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const configuredProviderIds = new Set(providers.filter(p => p.is_configured).map(p => p.id));
  const unconfiguredProviders = KNOWN_PROVIDERS.filter(p => !configuredProviderIds.has(p.id));

  return (
    <div className="space-y-4">
      <div
        className="p-4 rounded-xl border"
        style={{
          background: 'var(--base-02)',
          borderColor: 'var(--base-04)',
        }}
      >
        <h3 className="font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
          Add Provider
        </h3>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Add a new OpenAI-compatible or Anthropic-compatible API provider. You'll need to add its API key in Settings after adding the provider to config.
        </p>
        <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
          Provider config persistence is deferred to P115/P116. Manual config editing required until then.
        </p>
      </div>

      {!showForm ? (
        <div className="space-y-2">
          {unconfiguredProviders.length === 0 ? (
            <div className="text-center py-8 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              All known providers are already configured. Add API keys in Settings to enable them.
            </div>
          ) : (
            <div className="grid gap-2">
              {unconfiguredProviders.map(provider => (
                <button
                  key={provider.id}
                  onClick={() => setShowForm(true)}
                  className="flex items-center justify-between p-3 rounded-xl border text-left transition-colors hover:bg-[var(--base-01)]"
                  style={{
                    background: 'var(--base-02)',
                    borderColor: 'var(--base-04)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <div>
                    <div className="font-medium text-sm">{provider.name}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {provider.baseUrl}
                    </div>
                  </div>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div
          className="p-4 rounded-xl border"
          style={{
            background: 'var(--base-02)',
            borderColor: 'var(--base-04)',
          }}
        >
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            To add a new provider:
          </p>
          <ol className="mt-3 space-y-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <li className="flex gap-2">
              <span>1.</span>
              <span>Add the provider to <code className="px-1 rounded" style={{ background: 'var(--base-03)' }}>configs/litellm-config.yaml</code></span>
            </li>
            <li className="flex gap-2">
              <span>2.</span>
              <span>Add the API key to <code className="px-1 rounded" style={{ background: 'var(--base-03)' }}>~/.config/bazzite-ai/keys.env</code></span>
            </li>
            <li className="flex gap-2">
              <span>3.</span>
              <span>Refresh the providers panel</span>
            </li>
          </ol>
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 rounded-lg text-sm border"
              style={{
                background: 'var(--base-02)',
                borderColor: 'var(--base-04)',
                color: 'var(--text-primary)',
              }}
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
}