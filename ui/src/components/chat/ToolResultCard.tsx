"use client";

import React, { useState } from 'react';
import { ToolCall } from '@/types/chat';

interface ToolResultCardProps {
  toolCall: ToolCall;
}

export function ToolResultCard({ toolCall }: ToolResultCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const { name, arguments: args, argumentsSummary, result, status } = toolCall;

  const isPending = status === 'pending';
  const isSuccess = status === 'success';
  const isError = status === 'error';
  const isBlocked = status === 'blocked';

  return (
    <div
      className="rounded-lg border overflow-hidden motion-safe:transition-all motion-safe:duration-300"
      style={{
        background: 'var(--base-02)',
        borderColor: isError || isBlocked ? 'var(--danger)' : 'var(--base-04)',
        borderLeftWidth: '3px',
        borderLeftColor: isError
          ? 'var(--danger)'
          : isBlocked
          ? 'var(--warning)'
          : isSuccess
          ? 'var(--success)'
          : 'var(--warning)',
      }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-[var(--base-03)] transition-colors"
      >
        <div className="flex items-center gap-3">
          {/* Status Icon */}
          <div
            className="w-5 h-5 rounded-full flex items-center justify-center"
            style={{
              background: isPending
                ? 'var(--warning)'
                : isSuccess
                ? 'var(--success)'
                : isBlocked
                ? 'var(--warning)'
                : 'var(--danger)',
            }}
          >
            {isPending ? (
              <SpinnerIcon />
            ) : isSuccess ? (
              <CheckIcon />
            ) : isBlocked ? (
              <BlockedIcon />
            ) : (
              <ErrorIcon />
            )}
          </div>

          {/* Tool name and status */}
          <div className="flex items-center gap-2">
            <span
              className="text-sm font-medium"
              style={{ color: 'var(--text-primary)' }}
            >
              {name}
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: isPending
                  ? 'rgba(245, 158, 11, 0.1)'
                  : isSuccess
                  ? 'rgba(34, 197, 94, 0.1)'
                  : isBlocked
                  ? 'rgba(245, 158, 11, 0.1)'
                  : 'rgba(239, 68, 68, 0.1)',
                color: isPending
                  ? 'var(--warning)'
                  : isSuccess
                  ? 'var(--success)'
                  : isBlocked
                  ? 'var(--warning)'
                  : 'var(--danger)',
              }}
            >
              {isPending ? 'Running' : isSuccess ? 'Success' : isBlocked ? 'Blocked' : 'Error'}
            </span>
          </div>
          {argumentsSummary && (
            <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
              {argumentsSummary}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Duration */}
          {result && (
            <span
              className="text-xs"
              style={{ color: 'var(--text-tertiary)' }}
            >
              {result.duration}ms
            </span>
          )}

          {/* Expand/Collapse */}
          <div
            className={`transition-transform duration-200 ${
              isExpanded ? 'rotate-180' : ''
            }`}
            style={{ color: 'var(--text-tertiary)' }}
          >
            <ChevronIcon />
          </div>
        </div>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="border-t" style={{ borderColor: 'var(--base-04)' }}>
          {/* Arguments */}
          {Object.keys(args).length > 0 && (
            <div className="p-3 border-b" style={{ borderColor: 'var(--base-04)' }}>
              <div
                className="text-xs font-medium mb-2"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Arguments
              </div>
              <pre
                className="text-xs overflow-x-auto p-2 rounded"
                style={{
                  background: 'var(--base-03)',
                  color: 'var(--text-secondary)',
                }}
              >
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}

          {/* Result */}
          <div className="p-3">
            <div
              className="text-xs font-medium mb-2"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Result
            </div>
            {isPending ? (
              <div
                className="flex items-center gap-2 text-sm"
                style={{ color: 'var(--text-secondary)' }}
              >
                <SpinnerIcon />
                Executing...
              </div>
            ) : (isError || isBlocked) && result?.error ? (
              <div
                className="text-sm p-2 rounded"
                style={{
                  background: isBlocked ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                  color: isBlocked ? 'var(--warning)' : 'var(--danger)',
                }}
              >
                {result.error}
              </div>
            ) : result ? (
              <pre
                className="text-xs overflow-x-auto p-2 rounded max-h-60 overflow-y-auto"
                style={{
                  background: 'var(--base-03)',
                  color: 'var(--text-secondary)',
                }}
              >
                {formatResult(result.output)}
              </pre>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function formatResult(output: string | Record<string, unknown>): string {
  if (typeof output === 'string') {
    return output;
  }
  return JSON.stringify(output, null, 2);
}

// Icon components
function SpinnerIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="animate-spin"
      style={{ color: 'white' }}
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ color: 'white' }}
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ color: 'white' }}
    >
      <line x1="18" x2="6" y1="6" y2="18" />
      <line x1="6" x2="18" y1="6" y2="18" />
    </svg>
  );
}

function BlockedIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ color: 'white' }}
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="4" x2="20" y1="12" y2="12" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
