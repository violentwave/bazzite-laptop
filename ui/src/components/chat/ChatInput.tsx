"use client";

import React, { useState, useRef, useCallback } from 'react';
import { Attachment } from '@/types/chat';

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileSelect: (file: File) => void;
  attachedFiles: Attachment[];
  onRemoveFile: (id: string) => void;
  isStreaming: boolean;
  onStop: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onFileSelect,
  attachedFiles,
  onRemoveFile,
  isStreaming,
  onStop,
  disabled = false,
  placeholder = 'Type a message...',
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    adjustTextareaHeight();
  };

  const handleSend = () => {
    if (input.trim() || attachedFiles.length > 0) {
      onSend(input);
      setInput('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    files.forEach((file) => {
      if (validateFile(file)) {
        onFileSelect(file);
      }
    });
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach((file) => {
      if (validateFile(file)) {
        onFileSelect(file);
      }
    });
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const validateFile = (file: File): boolean => {
    // Max file size: 10MB
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert(`File ${file.name} is too large. Max size is 10MB.`);
      return false;
    }
    return true;
  };

  const hasContent = input.trim().length > 0 || attachedFiles.length > 0;

  return (
    <div
      className="relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div
          className="absolute inset-0 z-50 flex items-center justify-center rounded-xl border-2 border-dashed motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
          style={{
            background: 'var(--glass-bg)',
            backdropFilter: 'blur(8px)',
            borderColor: 'var(--accent-primary)',
          }}
        >
          <div className="text-center">
            <UploadIcon />
            <p
              className="mt-2 text-lg font-medium"
              style={{ color: 'var(--text-primary)' }}
            >
              Drop files here
            </p>
            <p style={{ color: 'var(--text-secondary)' }}>
              Images, documents, and text files
            </p>
          </div>
        </div>
      )}

      {/* Input container */}
      <div
        className="rounded-xl border"
        style={{
          background: 'var(--base-01)',
          borderColor: isDragging ? 'var(--accent-primary)' : 'var(--base-04)',
        }}
      >
        {/* Attached files */}
        {attachedFiles.length > 0 && (
          <div
            className="flex flex-wrap gap-2 p-3 border-b"
            style={{ borderColor: 'var(--base-04)' }}
          >
            {attachedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm group"
                style={{
                  background: 'var(--base-03)',
                  color: 'var(--text-secondary)',
                }}
              >
                {file.previewUrl ? (
                  <img
                    src={file.previewUrl}
                    alt={file.name}
                    className="w-6 h-6 rounded object-cover"
                  />
                ) : file.type.startsWith('image/') ? (
                  <ImageIcon />
                ) : (
                  <FileIcon />
                )}
                <span className="truncate max-w-[150px]">{file.name}</span>
                <button
                  onClick={() => onRemoveFile(file.id)}
                  className="ml-1 p-0.5 rounded hover:bg-[var(--base-04)] transition-colors"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  <CloseIcon />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Textarea */}
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isStreaming}
            rows={1}
            className="w-full bg-transparent resize-none outline-none px-4 py-3 pr-24 text-sm"
            style={{
              color: 'var(--text-primary)',
              minHeight: '48px',
              maxHeight: '200px',
            }}
          />

          {/* Action buttons */}
          <div className="absolute right-2 bottom-2 flex items-center gap-2">
            {/* File upload button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isStreaming}
              className="p-2 rounded-lg transition-colors disabled:opacity-50"
              style={{
                color: 'var(--text-tertiary)',
              }}
              title="Attach file"
            >
              <PaperclipIcon />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              accept="image/*,.pdf,.txt,.md,.json,.csv,.yaml,.yml"
            />

            {/* Send / Stop button */}
            {isStreaming ? (
              <button
                onClick={onStop}
                className="p-2 rounded-lg transition-colors"
                style={{
                  background: 'var(--danger)',
                  color: 'white',
                }}
                title="Stop generation"
              >
                <StopIcon />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!hasContent || disabled}
                className="p-2 rounded-lg transition-colors disabled:opacity-50"
                style={{
                  background: hasContent
                    ? 'var(--accent-primary)'
                    : 'var(--base-04)',
                  color: 'white',
                }}
                title="Send message"
              >
                <SendIcon />
              </button>
            )}
          </div>
        </div>

        {/* Footer */}
          <div
            className="flex items-center justify-between px-4 py-2 text-xs border-t"
            style={{
              borderColor: 'var(--base-04)',
              color: 'var(--text-tertiary)',
            }}
          >
            <div className="flex items-center gap-4">
              <span>Shift + Enter for newline</span>
              <span>Max file size 10MB</span>
            </div>
          <div className="flex items-center gap-2">
            {isStreaming && (
              <span className="flex items-center gap-1 animate-pulse">
                <span
                  className="w-1.5 h-1.5 rounded-full animate-pulse-live"
                  style={{ background: 'var(--live-cyan)' }}
                />
                Generating...
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Icon components
function UploadIcon() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      style={{ color: 'var(--accent-primary)', margin: '0 auto' }}
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" x2="12" y1="3" y2="15" />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
      <circle cx="9" cy="9" r="2" />
      <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <line x1="18" x2="6" y1="6" y2="18" />
      <line x1="6" x2="18" y1="6" y2="18" />
    </svg>
  );
}

function PaperclipIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <line x1="22" x2="11" y1="2" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="currentColor"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect width="14" height="14" x="5" y="5" rx="2" ry="2" />
    </svg>
  );
}
