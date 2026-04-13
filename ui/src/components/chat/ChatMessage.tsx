"use client";

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Message } from '@/types/chat';
import { ToolResultCard } from './ToolResultCard';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  switch (message.role) {
    case 'user':
      return <UserMessage message={message} />;
    case 'assistant':
      return (
        <AssistantMessage
          message={message}
          isStreaming={isStreaming}
        />
      );
    case 'tool':
      return <ToolMessage message={message} />;
    default:
      return null;
  }
}

function UserMessage({ message }: { message: Message }) {
  return (
    <div className="flex justify-end mb-4 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-right-2 motion-safe:duration-200">
      <div
        className="max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-3"
        style={{
          background: 'var(--base-03)',
          color: 'var(--text-primary)',
        }}
      >
        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {message.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm"
                style={{
                  background: 'var(--base-04)',
                  color: 'var(--text-secondary)',
                }}
              >
                {attachment.type.startsWith('image/') ? (
                  <ImageIcon />
                ) : (
                  <FileIcon />
                )}
                <span className="truncate max-w-[150px]">{attachment.name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Message content */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Timestamp */}
        <div
          className="text-xs mt-2 text-right"
          style={{ color: 'var(--text-tertiary)' }}
        >
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

function AssistantMessage({
  message,
  isStreaming,
}: {
  message: Message;
  isStreaming?: boolean;
}) {
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;

  return (
    <div className="flex justify-start mb-4 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-left-2 motion-safe:duration-200">
      <div
        className="max-w-[90%] rounded-lg pl-4 py-2"
        style={{
          borderLeft: '3px solid var(--accent-primary)',
          color: 'var(--text-primary)',
        }}
      >
        {/* Assistant avatar/label */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center"
            style={{ background: 'var(--accent-primary)' }}
          >
            <BotIcon />
          </div>
          <span
            className="text-xs font-medium"
            style={{ color: 'var(--text-secondary)' }}
          >
            Assistant
          </span>
          {isStreaming && (
            <span
              className="flex items-center gap-1 text-xs animate-pulse"
              style={{ color: 'var(--live-cyan)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-live" />
              Thinking...
            </span>
          )}
        </div>

        {/* Message content with markdown */}
        <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              code: CodeBlock,
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc pl-4 mb-2">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal pl-4 mb-2">{children}</ol>
              ),
              li: ({ children }) => <li className="mb-1">{children}</li>,
              a: ({ href, children }) => (
                <a
                  href={href}
                  className="text-[var(--accent-primary)] hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {children}
                </a>
              ),
              pre: ({ children }) => (
                <pre
                  className="rounded-lg p-3 overflow-x-auto mb-2 text-xs"
                  style={{
                    background: 'var(--base-02)',
                    border: '1px solid var(--base-04)',
                  }}
                >
                  {children}
                </pre>
              ),
            }}
          >
            {message.content || (isStreaming ? '' : '...')}
          </ReactMarkdown>
        </div>

        {/* Tool calls */}
        {hasToolCalls && (
          <div className="mt-3 space-y-2">
            {message.toolCalls?.map((toolCall) => (
              <ToolResultCard key={toolCall.id} toolCall={toolCall} />
            ))}
          </div>
        )}

        {/* Error display */}
        {message.error && (
          <div
            className="mt-3 p-3 rounded-lg text-sm"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid var(--danger)',
              color: 'var(--danger)',
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <ErrorIcon />
              <span className="font-medium">Error</span>
            </div>
            {message.error}
          </div>
        )}

        {/* Timestamp */}
        <div
          className="text-xs mt-2"
          style={{ color: 'var(--text-tertiary)' }}
        >
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

function ToolMessage({ message }: { message: Message }) {
  if (!message.toolCalls || message.toolCalls.length === 0) {
    return null;
  }

  return (
    <div className="flex justify-start mb-4 pl-8">
      <div className="w-full max-w-[90%]">
        {message.toolCalls.map((toolCall) => (
          <ToolResultCard key={toolCall.id} toolCall={toolCall} />
        ))}
      </div>
    </div>
  );
}

// Code block component with syntax highlighting
function CodeBlock({
  inline,
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<'code'> & { inline?: boolean }) {
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';

  if (inline) {
    return (
      <code
        className="px-1.5 py-0.5 rounded text-xs font-mono"
        style={{
          background: 'var(--base-03)',
          color: 'var(--text-primary)',
        }}
        {...props}
      >
        {children}
      </code>
    );
  }

  return (
    <div className="relative group">
      {/* Language label */}
      {language && (
        <div
          className="absolute top-2 right-2 text-xs px-2 py-1 rounded"
          style={{
            background: 'var(--base-04)',
            color: 'var(--text-tertiary)',
          }}
        >
          {language}
        </div>
      )}
      <code className={className} {...props}>
        {children}
      </code>
    </div>
  );
}

// Utility functions
function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - new Date(date).getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return new Date(date).toLocaleDateString();
}

// Icon components
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

function BotIcon() {
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
      <rect width="18" height="10" x="3" y="11" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" x2="12" y1="8" y2="12" />
      <line x1="12" x2="12.01" y1="16" y2="16" />
    </svg>
  );
}
