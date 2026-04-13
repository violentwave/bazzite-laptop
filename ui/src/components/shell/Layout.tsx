"use client";

import { ReactNode } from "react";
import { TopBar } from "./TopBar";
import { IconRail } from "./IconRail";
import { CommandPalette } from "./CommandPalette";
import { NotificationsPanel } from "./NotificationsPanel";
import { useShell } from "./ShellContext";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isRailExpanded, activePanel } = useShell();

  return (
    <div
      className="h-screen w-screen flex flex-col overflow-hidden"
      style={{
        background: "var(--base-01)",
        color: "var(--text-primary)",
      }}
    >
      {/* Top Bar */}
      <TopBar />

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Icon Rail */}
        <IconRail />

        {/* Content */}
        <main
          className="flex-1 flex flex-col min-w-0 overflow-hidden"
          style={{
            background: "var(--base-00)",
          }}
        >
          {/* Panel Content */}
          <div className="flex-1 overflow-auto">
            {children}
          </div>

          {/* Audit Strip - shown on privileged panels */}
          {activePanel === "settings" && <AuditStrip />}
        </main>

        {/* Notifications Panel */}
        <NotificationsPanel />
      </div>

      {/* Command Palette Overlay */}
      <CommandPalette />
    </div>
  );
}

function AuditStrip() {
  const { auditLog } = useShell();
  const lastEntry = auditLog[0];

  return (
    <div
      className="h-[32px] flex items-center justify-between px-4 text-xs shrink-0"
      style={{
        background: "var(--base-01)",
        borderTop: "1px solid var(--base-04)",
        color: "var(--text-secondary)",
      }}
    >
      <div className="flex items-center gap-2">
        <DocumentIcon />
        {lastEntry ? (
          <span>
            {lastEntry.action} {lastEntry.target && `- ${lastEntry.target}`}
          </span>
        ) : (
          <span>No recent actions</span>
        )}
      </div>
      {lastEntry && (
        <>
          <span style={{ color: "var(--text-tertiary)" }}>
            {formatTime(lastEntry.timestamp)}
          </span>
          <button
            className="hover:underline"
            style={{ color: "var(--accent-primary)" }}
          >
            History
          </button>
        </>
      )}
    </div>
  );
}

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);

  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  return date.toLocaleDateString();
}

function DocumentIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}
