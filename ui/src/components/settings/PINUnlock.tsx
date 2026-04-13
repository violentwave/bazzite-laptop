"use client";

import React, { useState } from 'react';

interface PINUnlockProps {
  onUnlock: (pin: string) => Promise<boolean>;
  lockoutStatus: {
    is_locked: boolean;
    remaining_seconds: number;
    failed_attempts: number;
    max_attempts: number;
  };
  onCancel: () => void;
}

export function PINUnlock({ onUnlock, lockoutStatus, onCancel }: PINUnlockProps) {
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (pin.length < 4) {
      setError('Please enter your PIN');
      return;
    }

    setIsSubmitting(true);
    try {
      const success = await onUnlock(pin);
      if (!success) {
        setError('Invalid PIN. Please try again.');
        setPin('');
      }
    } catch {
      setError('An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (lockoutStatus.is_locked) {
    return (
      <div
        className="max-w-md mx-auto p-6 rounded-xl border"
        style={{
          background: 'var(--base-02)',
          borderColor: 'var(--danger)',
        }}
      >
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(239, 68, 68, 0.2)' }}
          >
            <LockIcon />
          </div>
          <h2
            className="text-xl font-semibold"
            style={{ color: 'var(--danger)' }}
          >
            PIN Locked
          </h2>
        </div>

        <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
          Too many failed attempts. Please wait before trying again.
        </p>

        <div
          className="p-4 rounded-lg mb-4 text-center"
          style={{
            background: 'var(--base-03)',
            color: 'var(--text-primary)',
          }}
        >
          <div className="text-3xl font-mono font-bold mb-1">
            {formatTime(lockoutStatus.remaining_seconds)}
          </div>
          <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
            remaining
          </div>
        </div>

        <button
          onClick={onCancel}
          className="w-full px-4 py-2 rounded-lg transition-colors"
          style={{
            background: 'var(--base-03)',
            color: 'var(--text-secondary)',
          }}
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div
      className="max-w-md mx-auto p-6 rounded-xl border"
      style={{
        background: 'var(--base-02)',
        borderColor: 'var(--base-04)',
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center"
          style={{ background: 'var(--base-03)' }}
        >
          <LockIcon />
        </div>
        <h2
          className="text-xl font-semibold"
          style={{ color: 'var(--text-primary)' }}
        >
          Unlock Settings
        </h2>
      </div>

      <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
        Enter your PIN to access sensitive settings and API keys.
      </p>

      {lockoutStatus.failed_attempts > 0 && (
        <div
          className="mb-4 p-3 rounded-lg text-sm"
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid var(--warning)',
            color: 'var(--warning)',
          }}
        >
          Warning: {lockoutStatus.failed_attempts} of {lockoutStatus.max_attempts} attempts used.
          {lockoutStatus.failed_attempts >= 2 && ' One more failed attempt will lock your PIN.'}
        </div>
      )}

      {error && (
        <div
          className="mb-4 p-3 rounded-lg text-sm"
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--danger)',
            color: 'var(--danger)',
          }}
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            PIN
          </label>
          <input
            type="password"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
            className="w-full px-4 py-2 rounded-lg outline-none transition-colors text-center text-2xl tracking-widest"
            style={{
              background: 'var(--base-03)',
              border: '1px solid var(--base-04)',
              color: 'var(--text-primary)',
            }}
            placeholder="••••"
            autoFocus
            required
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2 rounded-lg transition-colors"
            style={{
              background: 'var(--base-03)',
              color: 'var(--text-secondary)',
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || pin.length < 4}
            className="flex-1 px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            style={{
              background: 'var(--accent-primary)',
              color: 'white',
            }}
          >
            {isSubmitting ? 'Unlocking...' : 'Unlock'}
          </button>
        </div>
      </form>
    </div>
  );
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function LockIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ color: 'var(--danger)' }}
    >
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}
