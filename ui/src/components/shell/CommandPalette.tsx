"use client";

import { useShell } from "./ShellContext";
import { useEffect, useState, useCallback } from "react";

interface Command {
  id: string;
  title: string;
  shortcut?: string;
  category: string;
  panel?: string;
}

const commands: Command[] = [
  { id: "goto-chat", title: "Go to Chat", shortcut: "⌘1", category: "Navigation", panel: "chat" },
  { id: "goto-security", title: "Go to Security", shortcut: "⌘2", category: "Navigation", panel: "security" },
  { id: "goto-models", title: "Go to Models", shortcut: "⌘3", category: "Navigation", panel: "models" },
  { id: "goto-terminal", title: "Go to Terminal", shortcut: "⌘4", category: "Navigation", panel: "terminal" },
  { id: "goto-projects", title: "Go to Projects", shortcut: "⌘5", category: "Navigation", panel: "projects" },
  { id: "goto-settings", title: "Go to Settings", shortcut: "⌘6", category: "Navigation", panel: "settings" },
];

export function CommandPalette() {
  const { isCommandPaletteOpen, closeCommandPalette, setActivePanel } = useShell();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filter commands based on search
  const filteredCommands = commands.filter((cmd) =>
    cmd.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cmd.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group commands by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = [];
    acc[cmd.category].push(cmd);
    return acc;
  }, {} as Record<string, Command[]>);

  // Reset selection when search changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [searchQuery]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Open with Cmd/Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        // Toggle is handled by the shell context
      }

      if (!isCommandPaletteOpen) return;

      switch (e.key) {
        case "Escape":
          closeCommandPalette();
          break;
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) =>
            Math.min(prev + 1, filteredCommands.length - 1)
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          const selectedCommand = filteredCommands[selectedIndex];
          if (selectedCommand) {
            executeCommand(selectedCommand);
          }
          break;
      }
    },
    [isCommandPaletteOpen, closeCommandPalette, filteredCommands, selectedIndex]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const executeCommand = (command: Command) => {
    if (command.panel) {
      setActivePanel(command.panel);
    }

    closeCommandPalette();
    setSearchQuery("");
  };

  if (!isCommandPaletteOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      style={{ background: "rgba(0, 0, 0, 0.5)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) closeCommandPalette();
      }}
    >
      <div
        className="w-full max-w-[640px] rounded-xl overflow-hidden"
        style={{
          background: "var(--glass-bg)",
          backdropFilter: "blur(var(--blur-lg))",
          border: "1px solid var(--glass-border)",
          boxShadow: "var(--shadow-xl)",
        }}
      >
        {/* Search Input */}
        <div
          className="flex items-center gap-3 px-4 py-4 border-b"
          style={{ borderColor: "var(--base-04)" }}
        >
          <SearchIcon />
          <input
            type="text"
            placeholder="Search commands, tools, settings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-transparent outline-none text-base"
            style={{ color: "var(--text-primary)" }}
            autoFocus
          />
          <kbd
            className="px-2 py-1 rounded text-xs"
            style={{
              background: "var(--base-03)",
              color: "var(--text-tertiary)",
              border: "1px solid var(--base-04)",
            }}
          >
            ESC
          </kbd>
        </div>

        {/* Commands List */}
        <div
          className="max-h-[400px] overflow-y-auto py-2"
          style={{ color: "var(--text-primary)" }}
        >
          {filteredCommands.length === 0 ? (
            <div
              className="px-4 py-8 text-center"
              style={{ color: "var(--text-secondary)" }}
            >
              No commands found
            </div>
          ) : (
            Object.entries(groupedCommands).map(([category, commands]) => (
              <div key={category}>
                {/* Category Header */}
                <div
                  className="px-4 py-2 text-xs font-medium uppercase tracking-wide"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {category}
                </div>

                {/* Commands */}
                {commands.map((command) => {
                  const globalIndex = filteredCommands.findIndex(
                    (c) => c.id === command.id
                  );
                  const isSelected = globalIndex === selectedIndex;

                  return (
                    <button
                      key={command.id}
                      onClick={() => executeCommand(command)}
                      className="w-full flex items-center justify-between px-4 py-2.5 transition-colors"
                      style={{
                        background: isSelected
                          ? "var(--base-03)"
                          : "transparent",
                        borderLeft: isSelected
                          ? "3px solid var(--accent-primary)"
                          : "3px solid transparent",
                      }}
                      onMouseEnter={() => setSelectedIndex(globalIndex)}
                    >
                      <span className="text-sm">{command.title}</span>
                      {command.shortcut && (
                        <kbd
                          className="px-1.5 py-0.5 rounded text-xs"
                          style={{
                            background: "var(--base-03)",
                            color: "var(--text-tertiary)",
                            border: "1px solid var(--base-04)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {command.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-between px-4 py-2 text-xs border-t"
          style={{
            borderColor: "var(--base-04)",
            color: "var(--text-tertiary)",
          }}
        >
          <div className="flex items-center gap-4">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
          </div>
          <span>{filteredCommands.length} navigation commands</span>
        </div>
      </div>
    </div>
  );
}

function SearchIcon() {
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
      style={{ color: "var(--text-secondary)" }}
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}
