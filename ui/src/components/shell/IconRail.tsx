"use client";

import { useShell } from "./ShellContext";

interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  zone: "public" | "operator" | "privileged";
}

const navItems: NavItem[] = [
  {
    id: "chat",
    icon: <ChatIcon />,
    label: "Chat",
    zone: "public",
  },
  {
    id: "tools",
    icon: <ToolIcon />,
    label: "Tools",
    zone: "operator",
  },
  {
    id: "security",
    icon: <ShieldIcon />,
    label: "Security",
    zone: "operator",
  },
  {
    id: "models",
    icon: <BotIcon />,
    label: "Models",
    zone: "operator",
  },
  {
    id: "terminal",
    icon: <TerminalIcon />,
    label: "Terminal",
    zone: "operator",
  },
  {
    id: "projects",
    icon: <ChartIcon />,
    label: "Projects",
    zone: "operator",
  },
  {
    id: "workbench",
    icon: <WorkbenchIcon />,
    label: "Workbench",
    zone: "operator",
  },
  {
    id: "settings",
    icon: <SettingsIcon />,
    label: "Settings",
    zone: "privileged",
  },
];

export function IconRail() {
  const { isRailExpanded, toggleRail, activePanel, setActivePanel } = useShell();

  return (
    <nav
      className="h-full flex flex-col shrink-0 transition-all duration-200"
      style={{
        width: isRailExpanded ? "200px" : "56px",
        background: "var(--base-01)",
        borderRight: "1px solid var(--base-04)",
      }}
    >
      {/* Navigation Items */}
      <div className="flex-1 py-2">
        {navItems.map((item) => (
          <NavButton
            key={item.id}
            item={item}
            isActive={activePanel === item.id}
            isExpanded={isRailExpanded}
            onClick={() => setActivePanel(item.id)}
          />
        ))}
      </div>

      {/* Collapse/Expand Button */}
      <div
        className="py-2 border-t"
        style={{ borderColor: "var(--base-04)" }}
      >
        <button
          onClick={toggleRail}
          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-base-03 transition-colors"
          style={{ color: "var(--text-secondary)" }}
          title={isRailExpanded ? "Collapse" : "Expand"}
        >
          {isRailExpanded ? <CollapseIcon /> : <ExpandIcon />}
          {isRailExpanded && (
            <span className="text-sm">Collapse</span>
          )}
        </button>
      </div>
    </nav>
  );
}

interface NavButtonProps {
  item: NavItem;
  isActive: boolean;
  isExpanded: boolean;
  onClick: () => void;
}

function NavButton({ item, isActive, isExpanded, onClick }: NavButtonProps) {
  // Zone-based styling
  const getZoneColor = () => {
    switch (item.zone) {
      case "privileged":
        return "var(--danger)";
      case "operator":
        return "var(--warning)";
      default:
        return undefined;
    }
  };

  const zoneColor = getZoneColor();

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 relative group"
      title={!isExpanded ? item.label : undefined}
    >
      {/* Active indicator - left border */}
      {isActive && (
        <div
          className="absolute left-0 top-0 bottom-0 w-[3px]"
          style={{
            background: zoneColor || "var(--accent-primary)",
          }}
        />
      )}

      <div
        className={`flex items-center gap-3 w-full px-4 py-3 transition-colors ${
          isActive
            ? "bg-base-03"
            : "hover:bg-base-03"
        }`}
        style={{
          color: isActive
            ? zoneColor || "var(--text-primary)"
            : "var(--text-secondary)",
        }}
      >
        <span className="shrink-0">{item.icon}</span>
        {isExpanded && (
          <span className="text-sm truncate">{item.label}</span>
        )}
      </div>
    </button>
  );
}

/* Icon Components */

function ChatIcon() {
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
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function ToolIcon() {
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
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function ShieldIcon() {
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
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function BotIcon() {
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
      <rect width="18" height="10" x="3" y="11" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
      <line x1="8" y1="16" x2="8" y2="16" />
      <line x1="16" y1="16" x2="16" y2="16" />
    </svg>
  );
}

function TerminalIcon() {
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
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function ChartIcon() {
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
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function SettingsIcon() {
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
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function WorkbenchIcon() {
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
      <path d="M3 7h18" />
      <path d="M6 7V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2" />
      <path d="M14 7V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2" />
      <rect x="4" y="7" width="16" height="13" rx="2" />
      <path d="M10 12h4" />
      <path d="M12 10v4" />
    </svg>
  );
}

function CollapseIcon() {
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
      <path d="m11 17-5-5 5-5" />
      <path d="m18 17-5-5 5-5" />
    </svg>
  );
}

function ExpandIcon() {
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
      <path d="m13 17 5-5-5-5" />
      <path d="m6 17 5-5-5-5" />
    </svg>
  );
}
