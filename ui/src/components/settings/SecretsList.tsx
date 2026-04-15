"use client";

import React, { useState } from 'react';

interface Secret {
  name: string;
  masked_value: string;
  category: string;
  is_set: boolean;
}

interface SecretsListProps {
  secrets: Secret[];
  onReveal: (keyName: string) => Promise<string | null>;
  onUpdate: (keyName: string, value: string) => Promise<boolean>;
  onDelete: (keyName: string) => Promise<boolean>;
  isUnlocked: boolean;
  onRequestUnlock: () => void;
}

export function SecretsList({
  secrets,
  onReveal,
  onUpdate,
  onDelete,
  isUnlocked,
  onRequestUnlock,
}: SecretsListProps) {
  const [revealedValues, setRevealedValues] = useState<Record<string, string>>({});
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [isLoading, setIsLoading] = useState<Record<string, boolean>>({});
  const [deleteConfirmKey, setDeleteConfirmKey] = useState<string | null>(null);

  const groupedSecrets = secrets.reduce((acc, secret) => {
    if (!acc[secret.category]) {
      acc[secret.category] = [];
    }
    acc[secret.category].push(secret);
    return acc;
  }, {} as Record<string, Secret[]>);

  const handleReveal = async (keyName: string) => {
    if (!isUnlocked) {
      onRequestUnlock();
      return;
    }

    setIsLoading((prev) => ({ ...prev, [keyName]: true }));
    try {
      const value = await onReveal(keyName);
      if (value) {
        setRevealedValues((prev) => ({ ...prev, [keyName]: value }));
      }
    } finally {
      setIsLoading((prev) => ({ ...prev, [keyName]: false }));
    }
  };

  const handleEdit = (secret: Secret) => {
    if (!isUnlocked) {
      onRequestUnlock();
      return;
    }
    setEditingKey(secret.name);
    setEditValue('');
  };

  const handleSave = async (keyName: string) => {
    setIsLoading((prev) => ({ ...prev, [keyName]: true }));
    try {
      const success = await onUpdate(keyName, editValue);
      if (success) {
        setEditingKey(null);
        setEditValue('');
      }
    } finally {
      setIsLoading((prev) => ({ ...prev, [keyName]: false }));
    }
  };

  const handleDelete = async (keyName: string) => {
    if (!isUnlocked) {
      onRequestUnlock();
      return;
    }

    if (deleteConfirmKey !== keyName) {
      setDeleteConfirmKey(keyName);
      return;
    }

    setIsLoading((prev) => ({ ...prev, [keyName]: true }));
    try {
      await onDelete(keyName);
      setDeleteConfirmKey(null);
    } finally {
      setIsLoading((prev) => ({ ...prev, [keyName]: false }));
    }
  };

  return (
    <div className="space-y-6">
      {Object.entries(groupedSecrets).map(([category, categorySecrets]) => (
        <div
          key={category}
          className="rounded-xl border"
          style={{
            background: 'var(--base-02)',
            borderColor: 'var(--base-04)',
          }}
        >
          <div
            className="px-4 py-3 border-b font-medium"
            style={{
              borderColor: 'var(--base-04)',
              color: 'var(--text-primary)',
            }}
          >
            {category}
          </div>

          <div className="divide-y" style={{ borderColor: 'var(--base-04)' }}>
            {categorySecrets.map((secret) => (
              <div
                key={secret.name}
                className="px-4 py-3 flex items-center justify-between gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div
                    className="font-medium text-sm mb-1"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {secret.name}
                  </div>

                  {editingKey === secret.name ? (
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-full px-3 py-1.5 rounded text-sm outline-none"
                      style={{
                        background: 'var(--base-03)',
                        border: '1px solid var(--accent-primary)',
                        color: 'var(--text-primary)',
                      }}
                      placeholder="Enter new value..."
                      autoFocus
                    />
                  ) : (
                    <div
                      className="font-mono text-sm"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      {revealedValues[secret.name] || secret.masked_value}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {!secret.is_set && (
                    <span
                      className="text-xs px-2 py-1 rounded-full"
                      style={{
                        background: 'var(--base-03)',
                        color: 'var(--text-tertiary)',
                      }}
                    >
                      Not Set
                    </span>
                  )}

                  {editingKey === secret.name ? (
                    <>
                      <button
                        onClick={() => handleSave(secret.name)}
                        disabled={isLoading[secret.name] || !editValue}
                        className="p-2 rounded-lg transition-colors disabled:opacity-50"
                        style={{
                          background: 'var(--success)',
                          color: 'white',
                        }}
                        title="Save"
                      >
                        <CheckIcon />
                      </button>
                      <button
                        onClick={() => {
                          setEditingKey(null);
                          setEditValue('');
                        }}
                        className="p-2 rounded-lg transition-colors"
                        style={{
                          background: 'var(--base-03)',
                          color: 'var(--text-secondary)',
                        }}
                        title="Cancel"
                      >
                        <CloseIcon />
                      </button>
                    </>
                  ) : (
                    <>
                      {revealedValues[secret.name] ? (
                        <button
                          onClick={() => {
                            setRevealedValues((prev) => {
                              const next = { ...prev };
                              delete next[secret.name];
                              return next;
                            });
                          }}
                          className="p-2 rounded-lg transition-colors"
                          style={{
                            background: 'var(--base-03)',
                            color: 'var(--text-secondary)',
                          }}
                          title="Hide"
                        >
                          <EyeOffIcon />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleReveal(secret.name)}
                          disabled={isLoading[secret.name]}
                          className="p-2 rounded-lg transition-colors disabled:opacity-50"
                          style={{
                            background: 'var(--base-03)',
                            color: 'var(--text-secondary)',
                          }}
                          title="Reveal"
                        >
                          <EyeIcon />
                        </button>
                      )}

                      <button
                        onClick={() => handleEdit(secret)}
                        disabled={isLoading[secret.name]}
                        className="p-2 rounded-lg transition-colors disabled:opacity-50"
                        style={{
                          background: 'var(--base-03)',
                          color: 'var(--text-secondary)',
                        }}
                        title="Edit"
                      >
                        <EditIcon />
                      </button>

                      <button
                        onClick={() => handleDelete(secret.name)}
                        disabled={isLoading[secret.name] || !secret.is_set}
                        className="p-2 rounded-lg transition-colors disabled:opacity-50"
                        style={{
                          background:
                            deleteConfirmKey === secret.name ? 'rgba(239, 68, 68, 0.2)' : 'var(--base-03)',
                          color: 'var(--danger)',
                        }}
                        title={deleteConfirmKey === secret.name ? 'Click again to confirm' : 'Delete'}
                      >
                        <TrashIcon />
                      </button>
                    </>
                  )}
                </div>
                {deleteConfirmKey === secret.name && (
                  <div className="text-xs mt-1" style={{ color: 'var(--warning)' }}>
                    Click delete again to confirm removal.
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// Icon components
function EyeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7c.78 0 1.53-.09 2.24-.26" />
      <path d="M2 2l20 20" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18" />
      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
