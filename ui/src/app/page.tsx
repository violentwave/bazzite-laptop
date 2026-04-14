"use client";

import { useShell } from "@/components/shell/ShellContext";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { SettingsContainer } from "@/components/settings/SettingsContainer";
import { ProvidersContainer } from "@/components/providers/ProvidersContainer";
import { SecurityContainer } from "@/components/security/SecurityContainer";

export default function Home() {
  const { activePanel } = useShell();

  return (
    <div className="h-full flex flex-col">
      {/* Panel Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b"
        style={{
          borderColor: "var(--base-04)",
          background: "var(--base-01)",
        }}
      >
        <div className="flex items-center gap-3">
          <PanelIcon panel={activePanel} />
          <h1
            className="text-lg font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            {getPanelTitle(activePanel)}
          </h1>
        </div>
        <PanelStatus panel={activePanel} />
      </div>

      {/* Panel Content */}
      <div className="flex-1 overflow-hidden">
        {activePanel === "chat" ? (
          <ChatContainer />
        ) : activePanel === "models" ? (
          <ProvidersContainer />
        ) : activePanel === "settings" ? (
          <SettingsContainer />
        ) : activePanel === "security" ? (
          <SecurityContainer />
        ) : (
          <div className="h-full overflow-auto p-6">
            <PanelContent panel={activePanel} />
          </div>
        )}
      </div>
    </div>
  );
}

function PanelIcon({ panel }: { panel: string }) {
  const iconStyle = { width: 20, height: 20 };

  switch (panel) {
    case "chat":
      return (
        <svg
          style={iconStyle}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    case "security":
      return (
        <svg
          style={iconStyle}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case "models":
      return (
        <svg
          style={iconStyle}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <rect width="18" height="10" x="3" y="11" rx="2" />
          <circle cx="12" cy="5" r="2" />
          <path d="M12 7v4" />
        </svg>
      );
    case "terminal":
      return (
        <svg
          style={iconStyle}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      );
    case "projects":
      return (
        <svg
          style={iconStyle}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      );
    case "settings":
      return (
        <svg
          style={iconStyle}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        </svg>
      );
    default:
      return null;
  }
}

function getPanelTitle(panel: string): string {
  const titles: Record<string, string> = {
    chat: "Chat Workspace",
    security: "Security Ops Center",
    models: "Models & Providers",
    terminal: "Terminal",
    projects: "Projects & Phases",
    settings: "Settings",
  };
  return titles[panel] || "Unknown Panel";
}

function PanelStatus({ panel }: { panel: string }) {
  // Different panels show different status indicators
  switch (panel) {
    case "chat":
      return (
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: "var(--base-02)",
            color: "var(--success)",
            border: "1px solid var(--base-04)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full animate-pulse-live"
            style={{ background: "var(--live-cyan)" }}
          />
          Live
        </div>
      );
    case "security":
      return (
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: "var(--base-02)",
            color: "var(--success)",
            border: "1px solid var(--base-04)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--success)" }}
          />
          System Secure
        </div>
      );
    case "models":
      return (
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: "var(--base-02)",
            color: "var(--text-secondary)",
            border: "1px solid var(--base-04)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--accent-primary)" }}
          />
          6 Providers
        </div>
      );
    case "terminal":
      return (
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: "var(--base-02)",
            color: "var(--text-secondary)",
            border: "1px solid var(--base-04)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--offline)" }}
          />
          No Session
        </div>
      );
    case "projects":
      return (
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: "var(--base-02)",
            color: "var(--text-secondary)",
            border: "1px solid var(--base-04)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--accent-primary)" }}
          />
          P80 In Progress
        </div>
      );
    case "settings":
      return (
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: "var(--base-02)",
            color: "var(--warning)",
            border: "1px solid var(--base-04)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--warning)" }}
          />
          PIN Required
        </div>
      );
    default:
      return null;
  }
}

function PanelContent({ panel }: { panel: string }) {
  switch (panel) {
    case "security":
      return <SecurityContainer />;
    case "models":
      return <ModelsPlaceholder />;
    case "terminal":
      return <TerminalPlaceholder />;
    case "projects":
      return <ProjectsPlaceholder />;
    case "settings":
      return <SettingsPlaceholder />;
    default:
      return <div>Unknown panel: {panel}</div>;
  }
}

// Placeholder Components for other panels
function SecurityPlaceholder() {
  return (
    <div className="space-y-6">
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ background: "var(--base-03)" }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ color: "var(--success)" }}
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 12 15 16 10" />
            </svg>
          </div>
          <div>
            <h3
              className="font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              Security Ops Center
            </h3>
            <p style={{ color: "var(--text-tertiary)" }}>
              Coming in P81
            </p>
          </div>
        </div>
        <p style={{ color: "var(--text-secondary)" }}>
          The Security Ops Center will provide threat intel dashboards, active
          alerts, scan status, and incident response capabilities.
        </p>
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-3 gap-4">
        <StatusCard
          title="Last Scan"
          value="2 hours ago"
          status="success"
        />
        <StatusCard
          title="Threats"
          value="0 detected"
          status="success"
        />
        <StatusCard
          title="Alerts"
          value="3 active"
          status="warning"
        />
      </div>
    </div>
  );
}

function ModelsPlaceholder() {
  return (
    <div className="space-y-6">
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="font-medium mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Models & Providers
        </h3>
        <p style={{ color: "var(--text-secondary)" }}>
          Provider management, health monitoring, and routing configuration
          coming in P82.
        </p>
      </div>

      {/* Provider List */}
      <div className="space-y-2">
        {["Gemini", "Groq", "Mistral", "OpenRouter", "z.ai", "Cerebras"].map(
          (provider) => (
            <div
              key={provider}
              className="flex items-center justify-between p-4 rounded-lg border"
              style={{
                background: "var(--base-02)",
                borderColor: "var(--base-04)",
              }}
            >
              <span style={{ color: "var(--text-primary)" }}>{provider}</span>
              <div
                className="flex items-center gap-2 px-3 py-1 rounded-full text-xs"
                style={{
                  background: "var(--base-03)",
                  color: "var(--success)",
                }}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: "var(--success)" }}
                />
                Online
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}

function TerminalPlaceholder() {
  return (
    <div
      className="h-full rounded-xl border overflow-hidden flex flex-col"
      style={{
        background: "var(--base-00)",
        borderColor: "var(--base-04)",
      }}
    >
      {/* Terminal Header */}
      <div
        className="flex items-center gap-2 px-4 py-2 border-b"
        style={{
          background: "var(--base-01)",
          borderColor: "var(--base-04)",
        }}
      >
        <div
          className="w-3 h-3 rounded-full"
          style={{ background: "var(--danger)" }}
        />
        <div
          className="w-3 h-3 rounded-full"
          style={{ background: "var(--warning)" }}
        />
        <div
          className="w-3 h-3 rounded-full"
          style={{ background: "var(--success)" }}
        />
        <span
          className="ml-4 text-sm"
          style={{ color: "var(--text-secondary)" }}
        >
          Terminal — Coming in P83
        </span>
      </div>

      {/* Terminal Content */}
      <div className="flex-1 p-4 font-mono text-sm">
        <p style={{ color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--accent-primary)" }}>$</span> echo "Terminal integration coming in P83"
        </p>
        <p style={{ color: "var(--text-primary)" }}>
          Terminal integration coming in P83
        </p>
        <p style={{ color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--accent-primary)" }}>$</span>{" "}
          <span className="animate-pulse">_</span>
        </p>
      </div>
    </div>
  );
}

function ProjectsPlaceholder() {
  return (
    <div className="space-y-6">
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="font-medium mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Projects & Phases
        </h3>
        <p style={{ color: "var(--text-secondary)" }}>
          Phase control, Notion sync status, and project management coming in
          P85.
        </p>
      </div>

      {/* Phase Timeline */}
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h4
          className="text-sm font-medium mb-4"
          style={{ color: "var(--text-secondary)" }}
        >
          Recent Phases
        </h4>
        <div className="space-y-3">
          {[
            { phase: "P80", name: "Chat Workspace", status: "In Progress" },
            { phase: "P79", name: "UI Shell Bootstrap", status: "Complete" },
            { phase: "P78", name: "Midnight Glass Design", status: "Complete" },
            { phase: "P77", name: "UI Architecture", status: "Complete" },
          ].map((item) => (
            <div
              key={item.phase}
              className="flex items-center justify-between py-2 border-b last:border-0"
              style={{ borderColor: "var(--base-04)" }}
            >
              <div className="flex items-center gap-3">
                <span
                  className="text-sm font-mono"
                  style={{ color: "var(--accent-primary)" }}
                >
                  {item.phase}
                </span>
                <span style={{ color: "var(--text-primary)" }}>
                  {item.name}
                </span>
              </div>
              <span
                className="text-xs px-2 py-1 rounded-full"
                style={{
                  background:
                    item.status === "Complete"
                      ? "rgba(34, 197, 94, 0.1)"
                      : "rgba(99, 102, 241, 0.1)",
                  color:
                    item.status === "Complete"
                      ? "var(--success)"
                      : "var(--accent-primary)",
                }}
              >
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SettingsPlaceholder() {
  return (
    <div className="space-y-6">
      {/* PIN Warning */}
      <div
        className="flex items-start gap-3 p-4 rounded-lg border-l-[3px]"
        style={{
          background: "rgba(245, 158, 11, 0.1)",
          borderColor: "var(--warning)",
        }}
      >
        <span>⚠️</span>
        <div>
          <h4
            className="font-medium mb-1"
            style={{ color: "var(--text-primary)" }}
          >
            Privileged Zone
          </h4>
          <p style={{ color: "var(--text-secondary)" }}>
            Settings access requires PIN authentication. PIN/2FA implementation
            coming in P84.
          </p>
        </div>
      </div>

      {/* Settings Sections */}
      <div
        className="p-6 rounded-xl border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="font-medium mb-4 pb-4 border-b"
          style={{
            color: "var(--text-primary)",
            borderColor: "var(--base-04)",
          }}
        >
          Security Settings
        </h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div style={{ color: "var(--text-primary)" }}>
                PIN Protection
              </div>
              <div
                className="text-sm"
                style={{ color: "var(--text-tertiary)" }}
              >
                Require PIN to access settings
              </div>
            </div>
            <div
              className="w-12 h-6 rounded-full relative"
              style={{ background: "var(--base-04)" }}
            >
              <div
                className="absolute top-1 left-1 w-4 h-4 rounded-full"
                style={{ background: "var(--text-tertiary)" }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div style={{ color: "var(--text-primary)" }}>
                Two-Factor Authentication
              </div>
              <div
                className="text-sm"
                style={{ color: "var(--text-tertiary)" }}
              >
                Status: Not configured
              </div>
            </div>
            <button
              className="px-4 py-2 rounded-lg text-sm transition-colors"
              style={{
                background: "var(--accent-primary)",
                color: "white",
              }}
            >
              Setup
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div style={{ color: "var(--text-primary)" }}>Gmail Alerts</div>
              <div
                className="text-sm"
                style={{ color: "var(--text-tertiary)" }}
              >
                Forward alerts to Gmail
              </div>
            </div>
            <div
              className="w-12 h-6 rounded-full relative"
              style={{ background: "var(--base-04)" }}
            >
              <div
                className="absolute top-1 left-1 w-4 h-4 rounded-full"
                style={{ background: "var(--text-tertiary)" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusCard({
  title,
  value,
  status,
}: {
  title: string;
  value: string;
  status: "success" | "warning" | "danger";
}) {
  const statusColors = {
    success: "var(--success)",
    warning: "var(--warning)",
    danger: "var(--danger)",
  };

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div
        className="text-sm mb-1"
        style={{ color: "var(--text-secondary)" }}
      >
        {title}
      </div>
      <div
        className="flex items-center gap-2 text-lg font-medium"
        style={{ color: statusColors[status] }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: statusColors[status] }}
        />
        {value}
      </div>
    </div>
  );
}
