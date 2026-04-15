"use client";

import { useRef, useEffect } from "react";
import { ShellSession, TerminalOutput } from "@/types/shell";

interface TerminalCanvasProps {
  output: TerminalOutput[];
  session: ShellSession | null;
  isLoading: boolean;
}

export function TerminalCanvas({ output, session, isLoading }: TerminalCanvasProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [output]);

  if (!session) {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center p-8"
        style={{ background: "var(--base-00)" }}
      >
        <div
          className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
          style={{ background: "var(--base-02)" }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            style={{ color: "var(--text-tertiary)" }}
          >
            <polyline points="4 17 10 11 4 5" />
            <line x1="12" y1="19" x2="20" y2="19" />
          </svg>
        </div>
        <h3
          className="text-lg font-medium mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          No Active Session
        </h3>
        <p
          className="text-sm text-center max-w-md mb-6"
          style={{ color: "var(--text-secondary)" }}
        >
          Create a new shell session to start executing commands in the terminal workspace.
        </p>
        <div
          className="text-xs px-4 py-2 rounded-lg"
          style={{
            background: "var(--base-02)",
            color: "var(--text-tertiary)",
          }}
        >
          Press &quot;+ New Session&quot; to begin
        </div>
      </div>
    );
  }

  if (session.status === "error") {
    const errorDetail = String(
      session.metadata?.error || "Failed to create shell session"
    );
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center p-8"
        style={{ background: "var(--base-00)" }}
      >
        <div
          className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
          style={{ background: "rgba(239, 68, 68, 0.1)" }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            style={{ color: "var(--danger)" }}
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <h3
          className="text-lg font-medium mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Session Error
        </h3>
        <p
          className="text-sm text-center max-w-md mb-4"
          style={{ color: "var(--text-secondary)" }}
        >
          {errorDetail}
        </p>
        <div
          className="text-xs px-4 py-2 rounded-lg"
          style={{
            background: "var(--base-02)",
            color: "var(--text-tertiary)",
          }}
        >
          Terminate this session and create a new one to continue
        </div>
      </div>
    );
  }

  if (session.status === "disconnected") {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center p-8"
        style={{ background: "var(--base-00)" }}
      >
        <div
          className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
          style={{ background: "var(--base-02)" }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            style={{ color: "var(--text-tertiary)" }}
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
          </svg>
        </div>
        <h3
          className="text-lg font-medium mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Session Disconnected
        </h3>
        <p
          className="text-sm text-center max-w-md mb-4"
          style={{ color: "var(--text-secondary)" }}
        >
          The shell process for this session is no longer running. Command history is preserved but no new commands can be executed.
        </p>
        <div
          className="text-xs px-4 py-2 rounded-lg"
          style={{
            background: "var(--base-02)",
            color: "var(--text-tertiary)",
          }}
        >
          Terminate this session and create a new one to continue
        </div>
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-auto p-4 font-mono text-sm"
      style={{
        background: "var(--base-00)",
        color: "var(--text-primary)",
        lineHeight: "1.6",
      }}
    >
      {/* Session Info Header */}
      <div
        className="mb-4 pb-3 border-b"
        style={{ borderColor: "var(--base-04)" }}
      >
        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-tertiary)" }}>
          <span>Session:</span>
          <span style={{ color: "var(--text-secondary)" }}>{session.name}</span>
          <span className="mx-2">|</span>
          <span>ID:</span>
          <span style={{ color: "var(--text-secondary)" }}>{session.id}</span>
          <span className="mx-2">|</span>
          <span>CWD:</span>
          <span style={{ color: "var(--text-secondary)" }}>{session.cwd}</span>
        </div>
      </div>

      {/* Terminal Output */}
      <div className="space-y-1">
        {output.length === 0 ? (
          <div
            className="text-sm italic"
            style={{ color: "var(--text-tertiary)" }}
          >
            Session started. Ready for commands.
          </div>
        ) : (
          output.map((line, index) => (
            <div
              key={index}
              className="whitespace-pre-wrap break-all"
              style={{
                color:
                  line.type === "error"
                    ? "var(--danger)"
                    : line.type === "input"
                    ? "var(--accent-primary)"
                    : line.type === "system"
                    ? "var(--text-tertiary)"
                    : "var(--text-primary)",
              }}
            >
              {line.content}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex items-center gap-2 mt-2">
            <div
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ background: "var(--live-cyan)" }}
            />
            <span
              className="text-xs italic"
              style={{ color: "var(--text-tertiary)" }}
            >
              Executing...
            </span>
          </div>
        )}
      </div>
    </div>
  );
}