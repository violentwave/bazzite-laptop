"use client";

import { useShell } from "./ShellContext";

export function TopBar() {
  const { openCommandPalette, toggleNotifications, isNotificationsOpen } = useShell();

  return (
    <header
      className="h-[48px] bg-base-01 border-b border-base-04 flex items-center justify-between px-4 shrink-0"
      style={{
        background: "var(--base-01)",
        borderBottom: "1px solid var(--base-04)",
      }}
    >
      {/* Left: Logo and App Menu */}
      <div className="flex items-center gap-3">
        <button
          className="p-2 rounded-md hover:bg-base-03 transition-colors"
          style={{ color: "var(--text-secondary)" }}
          aria-label="Open menu"
        >
          <MenuIcon />
        </button>
        <div className="flex items-center gap-2">
          <LightningIcon />
          <span
            className="font-semibold text-sm"
            style={{ color: "var(--text-primary)" }}
          >
            Bazzite
          </span>
          <span
            className="text-sm hidden sm:inline"
            style={{ color: "var(--text-secondary)" }}
          >
            Control Console
          </span>
        </div>
      </div>

      {/* Center: Context Indicator */}
      <div
        className="hidden md:flex items-center text-sm"
        style={{ color: "var(--text-tertiary)" }}
      >
        <span>Chat Workspace</span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        {/* Search / Command Palette Trigger */}
        <button
          onClick={openCommandPalette}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-base-03 transition-colors"
          style={{ color: "var(--text-secondary)" }}
          title="Open Command Palette (Ctrl+K)"
        >
          <SearchIcon />
          <span className="hidden sm:inline text-sm">Search</span>
          <kbd
            className="hidden lg:inline px-1.5 py-0.5 rounded text-xs"
            style={{
              background: "var(--base-03)",
              color: "var(--text-tertiary)",
              border: "1px solid var(--base-04)",
            }}
          >
            ⌘K
          </kbd>
        </button>

        {/* Notifications */}
        <button
          onClick={toggleNotifications}
          className={`p-2 rounded-md transition-colors relative ${
            isNotificationsOpen ? "bg-base-03" : "hover:bg-base-03"
          }`}
          style={{ color: "var(--text-secondary)" }}
          title="Notifications"
        >
          <BellIcon />
          {/* Notification badge - hidden when no notifications */}
          <span
            className="absolute top-1 right-1 w-2 h-2 rounded-full"
            style={{ background: "var(--danger)" }}
          />
        </button>

        {/* User / Settings */}
        <button
          className="p-2 rounded-md hover:bg-base-03 transition-colors"
          style={{ color: "var(--text-secondary)" }}
          title="Settings"
        >
          <UserIcon />
        </button>
      </div>
    </header>
  );
}

/* Icon Components */

function MenuIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

function LightningIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ color: "var(--accent-primary)" }}
    >
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}
