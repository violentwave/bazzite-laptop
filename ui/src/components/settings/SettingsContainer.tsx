"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { PINSetup } from './PINSetup';
import { PINUnlock } from './PINUnlock';
import { SecretsList } from './SecretsList';

interface Secret {
  name: string;
  masked_value: string;
  category: string;
  is_set: boolean;
}

interface LockoutStatus {
  is_locked: boolean;
  remaining_seconds: number;
  failed_attempts: number;
  max_attempts: number;
}

export function SettingsContainer() {
  const [pinStatus, setPinStatus] = useState<{
    pin_is_set: boolean;
    lockout: LockoutStatus;
  } | null>(null);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [showUnlock, setShowUnlock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch PIN status on mount
  useEffect(() => {
    fetchPinStatus();
    fetchSecrets();
  }, []);

  const fetchPinStatus = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'settings.pin_status' }),
      });
      const data = await response.json();
      setPinStatus(data);
    } catch (err) {
      setError('Failed to fetch PIN status');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSecrets = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'settings.list_secrets' }),
      });
      const data = await response.json();
      setSecrets(data);
    } catch (err) {
      setError('Failed to fetch secrets');
    }
  };

  const handleSetupPIN = async (pin: string): Promise<boolean> => {
    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'settings.setup_pin',
          arguments: { pin },
        }),
      });
      const data = await response.json();
      if (data.success) {
        setShowSetup(false);
        await fetchPinStatus();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const handleUnlock = async (pin: string): Promise<boolean> => {
    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'settings.verify_pin',
          arguments: { pin },
        }),
      });
      const data = await response.json();
      if (data.success) {
        setIsUnlocked(true);
        setShowUnlock(false);
        await fetchPinStatus();
        return true;
      }
      await fetchPinStatus();
      return false;
    } catch {
      return false;
    }
  };

  const handleRevealSecret = async (keyName: string): Promise<string | null> => {
    if (!isUnlocked) {
      setShowUnlock(true);
      return null;
    }

    // For demo purposes - in real implementation, would get PIN from a modal
    const pin = prompt('Enter your PIN to reveal the secret:');
    if (!pin) return null;

    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'settings.reveal_secret',
          arguments: { key_name: keyName, pin },
        }),
      });
      const data = await response.json();
      if (data.value) {
        return data.value;
      }
      return null;
    } catch {
      return null;
    }
  };

  const handleUpdateSecret = async (keyName: string, value: string): Promise<boolean> => {
    if (!isUnlocked) {
      setShowUnlock(true);
      return false;
    }

    const pin = prompt('Enter your PIN to update the secret:');
    if (!pin) return false;

    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'settings.set_secret',
          arguments: { key_name: keyName, value, pin },
        }),
      });
      const data = await response.json();
      if (data.success) {
        await fetchSecrets();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const handleDeleteSecret = async (keyName: string): Promise<boolean> => {
    if (!isUnlocked) {
      setShowUnlock(true);
      return false;
    }

    const pin = prompt('Enter your PIN to delete the secret:');
    if (!pin) return false;

    try {
      const response = await fetch('http://127.0.0.1:8766/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'settings.delete_secret',
          arguments: { key_name: keyName, pin },
        }),
      });
      const data = await response.json();
      if (data.success) {
        await fetchSecrets();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div
            className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }}
          />
          <p style={{ color: 'var(--text-secondary)' }}>Loading settings...</p>
        </div>
      </div>
    );
  }

  if (showSetup) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <PINSetup
          onSetup={handleSetupPIN}
          onCancel={() => setShowSetup(false)}
        />
      </div>
    );
  }

  if (showUnlock) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <PINUnlock
          onUnlock={handleUnlock}
          lockoutStatus={pinStatus?.lockout || {
            is_locked: false,
            remaining_seconds: 0,
            failed_attempts: 0,
            max_attempts: 3,
          }}
          onCancel={() => setShowUnlock(false)}
        />
      </div>
    );
  }

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
            Settings
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
            Manage API keys and sensitive configuration
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!pinStatus?.pin_is_set ? (
            <button
              onClick={() => setShowSetup(true)}
              className="px-4 py-2 rounded-lg transition-colors"
              style={{
                background: 'var(--warning)',
                color: 'white',
              }}
            >
              Set Up PIN
            </button>
          ) : isUnlocked ? (
            <div className="flex items-center gap-2">
              <span
                className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-full"
                style={{
                  background: 'rgba(34, 197, 94, 0.1)',
                  color: 'var(--success)',
                }}
              >
                <span className="w-2 h-2 rounded-full bg-current" />
                Unlocked
              </span>
              <button
                onClick={() => setIsUnlocked(false)}
                className="px-3 py-1.5 rounded-lg text-sm transition-colors"
                style={{
                  background: 'var(--base-03)',
                  color: 'var(--text-secondary)',
                }}
              >
                Lock
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowUnlock(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
              style={{
                background: 'var(--accent-primary)',
                color: 'white',
              }}
            >
              <LockIcon />
              Unlock Settings
            </button>
          )}
        </div>
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

        {!pinStatus?.pin_is_set ? (
          <div
            className="max-w-lg mx-auto p-6 rounded-xl border text-center"
            style={{
              background: 'var(--base-02)',
              borderColor: 'var(--warning)',
            }}
          >
            <div
              className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center"
              style={{ background: 'rgba(245, 158, 11, 0.1)' }}
            >
              <WarningIcon />
            </div>
            <h3
              className="text-lg font-medium mb-2"
              style={{ color: 'var(--text-primary)' }}
            >
              PIN Protection Required
            </h3>
            <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
              You need to set up a PIN before you can manage sensitive settings.
              This protects your API keys and other secrets.
            </p>
            <button
              onClick={() => setShowSetup(true)}
              className="px-4 py-2 rounded-lg transition-colors"
              style={{
                background: 'var(--accent-primary)',
                color: 'white',
              }}
            >
              Set Up PIN
            </button>
          </div>
        ) : (
          <SecretsList
            secrets={secrets}
            onReveal={handleRevealSecret}
            onUpdate={handleUpdateSecret}
            onDelete={handleDeleteSecret}
            isUnlocked={isUnlocked}
            onRequestUnlock={() => setShowUnlock(true)}
          />
        )}
      </div>

      {/* Audit Strip */}
      {isUnlocked && (
        <div
          className="h-[32px] flex items-center justify-between px-4 text-xs shrink-0"
          style={{
            background: 'var(--base-01)',
            borderTop: '1px solid var(--base-04)',
            color: 'var(--text-secondary)',
          }}
        >
          <div className="flex items-center gap-2">
            <ShieldIcon />
            <span>Settings unlocked</span>
          </div>
          <button
            className="hover:underline"
            style={{ color: 'var(--accent-primary)' }}
          >
            View Audit Log
          </button>
        </div>
      )}
    </div>
  );
}

// Icon components
function LockIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ color: 'var(--warning)' }}
    >
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" x2="12" y1="9" y2="13" />
      <line x1="12" x2="12.01" y1="17" y2="17" />
    </svg>
  );
}
