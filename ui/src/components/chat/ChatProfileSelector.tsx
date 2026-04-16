"use client";

import { useState, useEffect } from 'react';
import { TaskType, TASK_TYPE_LABELS, TASK_TYPE_DESCRIPTIONS } from '@/types/providers';

const STORAGE_KEY = 'bazzite-chat-profile';

const DEFAULT_PROFILE: TaskType = 'fast';

interface ChatProfileSelectorProps {
  onProfileChange?: (profile: TaskType) => void;
}

export function ChatProfileSelector({ onProfileChange }: ChatProfileSelectorProps) {
  const [selectedProfile, setSelectedProfile] = useState<TaskType>(DEFAULT_PROFILE);
  const [isOpen, setIsOpen] = useState(false);

  const taskTypes: TaskType[] = ['fast', 'reason', 'batch', 'code', 'embed'];

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && taskTypes.includes(stored as TaskType)) {
      setSelectedProfile(stored as TaskType);
      onProfileChange?.(stored as TaskType);
    }
  }, []);

  const handleSelect = (profile: TaskType) => {
    setSelectedProfile(profile);
    localStorage.setItem(STORAGE_KEY, profile);
    onProfileChange?.(profile);
    setIsOpen(false);
  };

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
        style={{
          background: 'var(--base-03)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--base-04)',
        }}
        title="Select chat profile"
      >
        <ProfileIcon />
        <span>{TASK_TYPE_LABELS[selectedProfile]}</span>
        <ChevronIcon className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div
          className="absolute bottom-full mb-2 left-0 z-50 min-w-[200px] rounded-lg shadow-lg overflow-hidden"
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
                background: selectedProfile === type ? 'var(--base-03)' : 'transparent',
                color: 'var(--text-primary)',
              }}
            >
              <div className="flex-1">
                <div className="font-medium">{TASK_TYPE_LABELS[type]}</div>
                <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {TASK_TYPE_DESCRIPTIONS[type]}
                </div>
              </div>
              {selectedProfile === type && <CheckIcon />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ProfileIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M12 2a4 4 0 0 1 4 4c0 1.1-.9 2-2 2s-2-.9-2-2a4 4 0 0 1 0-8" />
      <path d="M12 8v8" />
      <path d="M8 12H4" />
      <path d="M20 12h-4" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={className}
    >
      <path d="m6 9 6 6 6-6" />
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
      style={{ color: 'var(--accent-primary)' }}
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}