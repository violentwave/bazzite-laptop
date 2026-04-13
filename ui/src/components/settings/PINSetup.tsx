"use client";

import React, { useState, useEffect } from 'react';

interface PINSetupProps {
  onSetup: (pin: string) => Promise<boolean>;
  onCancel: () => void;
}

export function PINSetup({ onSetup, onCancel }: PINSetupProps) {
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (pin.length < 4 || pin.length > 6) {
      setError('PIN must be 4-6 digits');
      return;
    }

    if (!/^\d+$/.test(pin)) {
      setError('PIN must contain only numbers');
      return;
    }

    if (pin !== confirmPin) {
      setError('PINs do not match');
      return;
    }

    setIsSubmitting(true);
    try {
      const success = await onSetup(pin);
      if (!success) {
        setError('Failed to set PIN. Please try again.');
      }
    } catch {
      setError('An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="max-w-md mx-auto p-6 rounded-xl border"
      style={{
        background: 'var(--base-02)',
        borderColor: 'var(--base-04)',
      }}
    >
      <h2
        className="text-xl font-semibold mb-4"
        style={{ color: 'var(--text-primary)' }}
      >
        Set Up PIN Protection
      </h2>

      <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>
        Create a 4-6 digit PIN to protect sensitive settings. You&apos;ll need this PIN
        to view or modify API keys and other secrets.
      </p>

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
            Enter PIN
          </label>
          <input
            type="password"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
            className="w-full px-4 py-2 rounded-lg outline-none transition-colors"
            style={{
              background: 'var(--base-03)',
              border: '1px solid var(--base-04)',
              color: 'var(--text-primary)',
            }}
            placeholder="••••"
            required
          />
        </div>

        <div>
          <label
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            Confirm PIN
          </label>
          <input
            type="password"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={confirmPin}
            onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ''))}
            className="w-full px-4 py-2 rounded-lg outline-none transition-colors"
            style={{
              background: 'var(--base-03)',
              border: '1px solid var(--base-04)',
              color: 'var(--text-primary)',
            }}
            placeholder="••••"
            required
          />
        </div>

        <div className="flex gap-3 pt-4">
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
            disabled={isSubmitting}
            className="flex-1 px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            style={{
              background: 'var(--accent-primary)',
              color: 'white',
            }}
          >
            {isSubmitting ? 'Setting up...' : 'Set PIN'}
          </button>
        </div>
      </form>

      <div
        className="mt-6 p-3 rounded-lg text-sm"
        style={{
          background: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid var(--warning)',
          color: 'var(--text-secondary)',
        }}
      >
        <strong>Security Note:</strong> Your PIN is stored securely using PBKDF2
        hashing. After 3 failed attempts, you&apos;ll be locked out for 5 minutes.
      </div>
    </div>
  );
}
