"use client";

import React, { useState } from 'react';
import { ProviderInfo } from '@/types/providers';
import { callMCPTool } from '@/lib/mcp-client';

interface AddProviderPanelProps {
  providers: ProviderInfo[];
  onProviderAdded?: () => void;
}

const KNOWN_PROVIDERS = [
  { id: 'openai', name: 'OpenAI', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1', type: 'openai' },
  { id: 'anthropic', name: 'Anthropic', apiKeyEnv: 'ANTHROPIC_API_KEY', baseUrl: 'https://api.anthropic.com', type: 'anthropic' },
  { id: 'groq', name: 'Groq', apiKeyEnv: 'GROQ_API_KEY', baseUrl: 'https://api.groq.com/openai/v1', type: 'openai' },
  { id: 'mistral', name: 'Mistral', apiKeyEnv: 'MISTRAL_API_KEY', baseUrl: 'https://api.mistral.ai/v1', type: 'openai' },
  { id: 'gemini', name: 'Google Gemini', apiKeyEnv: 'GEMINI_API_KEY', baseUrl: 'https://generativelanguage.googleapis.com/v1', type: 'openai' },
  { id: 'openrouter', name: 'OpenRouter', apiKeyEnv: 'OPENROUTER_API_KEY', baseUrl: 'https://openrouter.ai/api/v1', type: 'openai' },
  { id: 'cerebras', name: 'Cerebras', apiKeyEnv: 'CEREBRAS_API_KEY', baseUrl: 'https://api.cerebras.ai', type: 'openai' },
  { id: 'zhipuai', name: 'Zhipuai', apiKeyEnv: 'ZAI_API_KEY', baseUrl: 'https://api.z.ai/api/paas/v1', type: 'openai' },
  { id: 'ollama', name: 'Ollama (Local)', apiKeyEnv: null, baseUrl: 'http://localhost:11434', type: 'openai' },
];

export function AddProviderPanel({ providers, onProviderAdded }: AddProviderPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    provider_id: '',
    display_name: '',
    provider_type: 'openai',
    base_url: '',
    credential_ref: '',
    notes: '',
  });

  const configuredProviderIds = new Set(providers.filter(p => p.is_configured).map(p => p.id));
  const unconfiguredProviders = KNOWN_PROVIDERS.filter(p => !configuredProviderIds.has(p.id));

  const handlePredefinedClick = (provider: typeof KNOWN_PROVIDERS[0]) => {
    setFormData({
      provider_id: provider.id,
      display_name: provider.name,
      provider_type: provider.type,
      base_url: provider.baseUrl,
      credential_ref: provider.apiKeyEnv || '',
      notes: '',
    });
    setShowForm(true);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.provider_id || !formData.display_name || !formData.provider_type) {
      setError('Provider ID, Display Name, and Type are required.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await callMCPTool('provider.create', {
        provider_id: formData.provider_id,
        display_name: formData.display_name,
        provider_type: formData.provider_type,
        base_url: formData.base_url || undefined,
        credential_ref: formData.credential_ref || undefined,
        notes: formData.notes || undefined,
      }) as any;

      if (response && response.success === false) {
        throw new Error(response.error || 'Failed to create provider');
      }

      setShowForm(false);
      setFormData({
        provider_id: '',
        display_name: '',
        provider_type: 'openai',
        base_url: '',
        credential_ref: '',
        notes: '',
      });
      
      if (onProviderAdded) {
        onProviderAdded();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

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
          Configure a new LLM provider. Once added, you can provide its API key in Settings.
        </p>
      </div>

      {!showForm ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h4 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Quick Add</h4>
            <button
              onClick={() => {
                setFormData({
                  provider_id: '',
                  display_name: '',
                  provider_type: 'openai',
                  base_url: '',
                  credential_ref: '',
                  notes: '',
                });
                setShowForm(true);
                setError(null);
              }}
              className="text-xs px-3 py-1.5 rounded-lg border transition-colors hover:bg-[var(--base-03)]"
              style={{
                background: 'var(--base-02)',
                borderColor: 'var(--base-04)',
                color: 'var(--text-primary)',
              }}
            >
              + Custom Provider
            </button>
          </div>
          
          {unconfiguredProviders.length === 0 ? (
            <div className="text-center py-8 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              All standard providers are already configured. You can still add custom providers.
            </div>
          ) : (
            <div className="grid gap-2">
              {unconfiguredProviders.map(provider => (
                <button
                  key={provider.id}
                  onClick={() => handlePredefinedClick(provider)}
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
        <form 
          onSubmit={handleSubmit}
          className="p-4 rounded-xl border space-y-4"
          style={{
            background: 'var(--base-02)',
            borderColor: 'var(--base-04)',
          }}
        >
          {error && (
            <div className="p-3 rounded-lg text-sm" style={{ background: 'var(--danger-bg)', color: 'var(--danger)', borderColor: 'var(--danger-border)' }}>
              {error}
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Provider ID</label>
              <input
                type="text"
                value={formData.provider_id}
                onChange={e => setFormData({...formData, provider_id: e.target.value})}
                className="w-full px-3 py-2 text-sm rounded-lg border"
                style={{ background: 'var(--base-01)', borderColor: 'var(--base-04)', color: 'var(--text-primary)' }}
                placeholder="e.g., custom_openai"
                required
              />
            </div>
            
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Display Name</label>
              <input
                type="text"
                value={formData.display_name}
                onChange={e => setFormData({...formData, display_name: e.target.value})}
                className="w-full px-3 py-2 text-sm rounded-lg border"
                style={{ background: 'var(--base-01)', borderColor: 'var(--base-04)', color: 'var(--text-primary)' }}
                placeholder="e.g., Custom OpenAI"
                required
              />
            </div>
          </div>
          
          <div className="space-y-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Provider Type</label>
            <select
              value={formData.provider_type}
              onChange={e => setFormData({...formData, provider_type: e.target.value})}
              className="w-full px-3 py-2 text-sm rounded-lg border"
              style={{ background: 'var(--base-01)', borderColor: 'var(--base-04)', color: 'var(--text-primary)' }}
            >
              <option value="openai">OpenAI Compatible (Most Common)</option>
              <option value="anthropic">Anthropic Compatible</option>
            </select>
          </div>
          
          <div className="space-y-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Base URL</label>
            <input
              type="url"
              value={formData.base_url}
              onChange={e => setFormData({...formData, base_url: e.target.value})}
              className="w-full px-3 py-2 text-sm rounded-lg border"
              style={{ background: 'var(--base-01)', borderColor: 'var(--base-04)', color: 'var(--text-primary)' }}
              placeholder="e.g., https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Credential Reference (Env Var)</label>
            <input
              type="text"
              value={formData.credential_ref}
              onChange={e => setFormData({...formData, credential_ref: e.target.value})}
              className="w-full px-3 py-2 text-sm rounded-lg border"
              style={{ background: 'var(--base-01)', borderColor: 'var(--base-04)', color: 'var(--text-primary)' }}
              placeholder="e.g., CUSTOM_API_KEY"
            />
          </div>
          
          <div className="space-y-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Notes</label>
            <input
              type="text"
              value={formData.notes}
              onChange={e => setFormData({...formData, notes: e.target.value})}
              className="w-full px-3 py-2 text-sm rounded-lg border"
              style={{ background: 'var(--base-01)', borderColor: 'var(--base-04)', color: 'var(--text-primary)' }}
              placeholder="Optional notes"
            />
          </div>

          <div className="pt-2 flex gap-3">
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                background: 'var(--accent)',
                color: 'white',
                opacity: isSubmitting ? 0.7 : 1,
              }}
            >
              {isSubmitting ? 'Saving...' : 'Save Provider'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg text-sm border transition-colors hover:bg-[var(--base-03)]"
              style={{
                background: 'var(--base-02)',
                borderColor: 'var(--base-04)',
                color: 'var(--text-primary)',
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
