"use client";

import React, { useState, useEffect } from 'react';
import { PINSetup } from './PINSetup';
import { PINUnlock } from './PINUnlock';
import { SecretsList } from './SecretsList';
import { callMCPTool } from '@/lib/mcp-client';

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

interface ToolResult {
  success?: boolean;
  error?: string;
  error_code?: string;
  operator_action?: string;
  lockout?: LockoutStatus;
  value?: string;
}

function formatOperatorError(prefix: string, data: ToolResult): string {
  // PIN-related errors
  if (data.error_code === 'pin_not_initialized') {
    return 'PIN not initialized. Set up PIN to continue.';
  }
  if (data.error_code === 'pin_already_initialized') {
    return 'PIN already set up. Use unlock flow with existing PIN.';
  }
  if (data.error_code === 'pin_invalid') {
    return 'PIN invalid. Retry with the configured PIN.';
  }
  if (data.error_code === 'pin_locked') {
    const seconds = data.lockout?.remaining_seconds ?? 0;
    const minutes = Math.ceil(seconds / 60);
    return `PIN locked. Wait ${minutes} minute${minutes !== 1 ? 's' : ''} before retrying.`;
  }
  if (data.error_code === 'pin_required') {
    return 'PIN required. Enter your PIN to continue.';
  }
  if (data.error_code === 'pin_validation_failed') {
    return `PIN validation failed: ${data.error || 'Enter a 4-6 digit PIN'}`;
  }
  if (data.error_code === 'pin_setup_failed') {
    return `PIN setup failed: ${data.error || 'Check settings database permissions'}`;
  }

  // Secrets-related errors
  if (data.error_code === 'secrets_unavailable') {
    return 'Secrets unavailable. Check settings backend and keys file access.';
  }
  if (data.error_code === 'keys_file_not_found') {
    return 'API keys file not found. Add API keys to enable secrets management.';
  }
  if (data.error_code === 'keys_file_permission_denied') {
    return 'Permission denied accessing API keys file. Check file permissions.';
  }
  if (data.error_code === 'secret_not_found') {
    return `Secret not found: ${data.error || 'Choose an existing key from the list'}`;
  }
  if (data.error_code === 'reveal_failed') {
    return `Failed to reveal secret: ${data.error || 'Check settings service health'}`;
  }
  if (data.error_code === 'set_secret_failed') {
    return `Failed to update secret: ${data.error || 'Check settings service health'}`;
  }
  if (data.error_code === 'delete_secret_failed') {
    return `Failed to delete secret: ${data.error || 'Check settings service health'}`;
  }

  // Backend errors
  if (data.error_code === 'settings_backend_unavailable') {
    return 'Settings backend unavailable. Ensure MCP bridge is running.';
  }
  if (data.error_code === 'unlock_failed') {
    return `Unlock failed: ${data.error || 'Check settings service health'}`;
  }
  if (data.error_code === 'audit_log_unavailable') {
    return 'Audit log unavailable. Check settings service health.';
  }

  // Generic fallback
  if (data.operator_action) {
    return `${prefix}: ${data.error || 'Operator action required'} (${data.operator_action})`;
  }
  if (data.error) {
    return `${prefix}: ${data.error}`;
  }
  return `${prefix}: operator action required`;
}

function classifyBackendError(err: unknown, context: 'settings' | 'secrets'): string {
  const msg = err instanceof Error ? err.message : String(err);
  const lowerMsg = msg.toLowerCase();

  // Connection errors
  if (lowerMsg.includes('failed to fetch') || lowerMsg.includes('network')) {
    return `Cannot connect to MCP bridge. Ensure the bridge is running on port 8766.`;
  }
  if (lowerMsg.includes('timeout')) {
    return `Request timed out. MCP bridge may be overloaded or unresponsive.`;
  }

  // MCP-specific errors
  if (lowerMsg.includes('mcp') && lowerMsg.includes('not initialized')) {
    return `MCP session not initialized. Refresh the page to reconnect.`;
  }

  // Context-specific messages
  if (context === 'settings') {
    if (lowerMsg.includes('permission') || lowerMsg.includes('access')) {
      return `Settings permission denied. Check file permissions on settings database.`;
    }
    return `Settings backend error: ${msg}`;
  }

  if (context === 'secrets') {
    if (lowerMsg.includes('permission') || lowerMsg.includes('access')) {
      return `Secrets access denied. Check file permissions on keys.env.`;
    }
    return `Secrets service error: ${msg}`;
  }

  return `Backend error: ${msg}`;
}

export function SettingsContainer() {
  const [pinStatus, setPinStatus] = useState<{
    pin_is_set: boolean;
    lockout: LockoutStatus;
  } | null>(null);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [actionPin, setActionPin] = useState('');
  const [showSetup, setShowSetup] = useState(false);
  const [showUnlock, setShowUnlock] = useState(false);
  const [showAuditLog, setShowAuditLog] = useState(false);
  const [auditLog, setAuditLog] = useState<Array<Record<string, unknown>>>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch PIN status on mount
  useEffect(() => {
    fetchPinStatus();
    fetchSecrets();
  }, []);

  const fetchPinStatus = async () => {
    try {
      const data = await callMCPTool('settings.pin_status');
      if (data && typeof data === 'object') {
        const result = data as ToolResult;
        // Check if backend returned an error
        if (result.success === false) {
          setError(formatOperatorError('PIN status check failed', result));
          return;
        }
        setError(null);
        setPinStatus(data as { pin_is_set: boolean; lockout: LockoutStatus });
      }
    } catch (err) {
      setError(classifyBackendError(err, 'settings'));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSecrets = async () => {
    try {
      const data = await callMCPTool('settings.list_secrets');
      // Success: data is an array of secrets
      if (Array.isArray(data)) {
        setSecrets(data as Secret[]);
        setError(null);
        return;
      }

      // Error: data is an error object
      if (data && typeof data === 'object') {
        const result = data as ToolResult;
        if (result.success === false) {
          // Check for specific error codes that don't require showing an error
          if (result.error_code === 'keys_file_not_found') {
            // Keys file doesn't exist yet - show empty secrets list
            setSecrets([]);
            setError(null);
            return;
          }
          setError(formatOperatorError('Secrets unavailable', result));
          return;
        }
      }

      // Unknown response format
      setSecrets([]);
    } catch (err) {
      setError(classifyBackendError(err, 'secrets'));
    }
  };

  const handleSetupPIN = async (pin: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const data = (await callMCPTool('settings.setup_pin', { pin })) as ToolResult;
      if (data.success) {
        setError(null);
        setShowSetup(false);
        await fetchPinStatus();
        return { success: true };
      }
      const msg = formatOperatorError('PIN setup failed', data);
      setError(msg);
      return { success: false, error: msg };
    } catch (err) {
      const msg = classifyBackendError(err, 'settings');
      setError(msg);
      return { success: false, error: msg };
    }
  };

  const handleUnlock = async (pin: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const data = (await callMCPTool('settings.verify_pin', { pin })) as ToolResult;
      if (data.success) {
        setError(null);
        setIsUnlocked(true);
        setActionPin(pin);
        setShowUnlock(false);
        await fetchPinStatus();
        return { success: true };
      }
      const msg = formatOperatorError('Unlock failed', data);
      setError(msg);
      await fetchPinStatus();
      return { success: false, error: msg };
    } catch (err) {
      const msg = classifyBackendError(err, 'settings');
      setError(msg);
      return { success: false, error: msg };
    }
  };

  const handleRevealSecret = async (keyName: string): Promise<string | null> => {
    if (!isUnlocked) {
      setShowUnlock(true);
      return null;
    }
    if (!actionPin) {
      setError('Action PIN required. Enter PIN in the security strip to reveal secrets.');
      return null;
    }

    try {
      const data = (await callMCPTool('settings.reveal_secret', {
        key_name: keyName,
        pin: actionPin,
      })) as ToolResult;
      if (data.value) {
        setError(null);
        return data.value;
      }
      setError(formatOperatorError('Reveal failed', data));
      return null;
    } catch (err) {
      setError(classifyBackendError(err, 'secrets'));
      return null;
    }
  };

  const handleUpdateSecret = async (keyName: string, value: string): Promise<boolean> => {
    if (!isUnlocked) {
      setShowUnlock(true);
      return false;
    }
    if (!actionPin) {
      setError('Action PIN required. Enter PIN in the security strip to update secrets.');
      return false;
    }

    try {
      const data = (await callMCPTool('settings.set_secret', {
        key_name: keyName,
        value,
        pin: actionPin,
      })) as ToolResult;
      if (data.success) {
        setError(null);
        await fetchSecrets();
        return true;
      }
      setError(formatOperatorError('Secret update failed', data));
      return false;
    } catch (err) {
      setError(classifyBackendError(err, 'secrets'));
      return false;
    }
  };

  const handleDeleteSecret = async (keyName: string): Promise<boolean> => {
    if (!isUnlocked) {
      setShowUnlock(true);
      return false;
    }

    if (!actionPin) {
      setError('Action PIN required. Enter PIN in the security strip to delete secrets.');
      return false;
    }

    try {
      const data = (await callMCPTool('settings.delete_secret', {
        key_name: keyName,
        pin: actionPin,
      })) as ToolResult;
      if (data.success) {
        setError(null);
        await fetchSecrets();
        return true;
      }
      setError(formatOperatorError('Secret delete failed', data));
      return false;
    } catch (err) {
      setError(classifyBackendError(err, 'secrets'));
      return false;
    }
  };

  const handleViewAuditLog = async () => {
    setAuditLoading(true);
    try {
      const data = (await callMCPTool('settings.audit_log')) as {
        success?: boolean;
        entries?: Array<Record<string, unknown>>;
        error?: string;
        error_code?: string;
      };
      if (data.success === false) {
        setError(formatOperatorError('Audit log unavailable', data));
        return;
      }
      setAuditLog(data.entries || []);
      setShowAuditLog(true);
    } catch (err) {
      setError(classifyBackendError(err, 'settings'));
    } finally {
      setAuditLoading(false);
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
          <>
            {isUnlocked && (
              <div
                className="mb-4 p-3 rounded-lg border"
                style={{
                  background: 'var(--base-02)',
                  borderColor: 'var(--base-04)',
                }}
              >
                <label
                  className="block text-xs mb-2"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  Action PIN (used for reveal/update/delete)
                </label>
                <input
                  type="password"
                  value={actionPin}
                  onChange={(e) => setActionPin(e.target.value)}
                  className="w-full max-w-xs px-3 py-2 rounded-md text-sm outline-none"
                  style={{
                    background: 'var(--base-03)',
                    border: '1px solid var(--base-04)',
                    color: 'var(--text-primary)',
                  }}
                  placeholder="Enter PIN"
                />
              </div>
            )}
            <SecretsList
              secrets={secrets}
              onReveal={handleRevealSecret}
              onUpdate={handleUpdateSecret}
              onDelete={handleDeleteSecret}
              isUnlocked={isUnlocked}
              onRequestUnlock={() => setShowUnlock(true)}
            />
          </>
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
            onClick={() => {
              void handleViewAuditLog();
            }}
            disabled={auditLoading}
            className="hover:underline"
            style={{ color: 'var(--accent-primary)' }}
          >
            {auditLoading ? 'Loading Audit Log...' : 'View Audit Log'}
          </button>
        </div>
      )}

      {showAuditLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
          <div
            className="w-full max-w-3xl max-h-[80vh] overflow-hidden rounded-xl border"
            style={{
              background: 'var(--base-01)',
              borderColor: 'var(--base-04)',
            }}
          >
            <div
              className="flex items-center justify-between px-4 py-3 border-b"
              style={{ borderColor: 'var(--base-04)' }}
            >
              <h3 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                Settings Audit Log
              </h3>
              <button
                onClick={() => setShowAuditLog(false)}
                className="text-xs px-2 py-1 rounded"
                style={{ background: 'var(--base-03)', color: 'var(--text-secondary)' }}
              >
                Close
              </button>
            </div>
            <div className="max-h-[65vh] overflow-auto p-4">
              {auditLog.length === 0 ? (
                <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                  No audit entries yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {auditLog.map((entry, idx) => (
                    <div
                      key={`${String(entry.timestamp || idx)}-${idx}`}
                      className="p-3 rounded border text-xs"
                      style={{
                        background: 'var(--base-02)',
                        borderColor: 'var(--base-04)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <div><strong>Time:</strong> {String(entry.timestamp || 'unknown')}</div>
                      <div><strong>Action:</strong> {String(entry.action || 'unknown')}</div>
                      <div><strong>Key:</strong> {String(entry.key_name || 'n/a')}</div>
                      <div><strong>Success:</strong> {String(entry.success ?? false)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
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
