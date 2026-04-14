"use client";

interface NextActionsPanelProps {
  recommendations: string[];
  isLoading: boolean;
}

export function NextActionsPanel({ recommendations, isLoading }: NextActionsPanelProps) {
  if (isLoading) {
    return (
      <div
        className="p-4 rounded-lg border"
        style={{
          background: "var(--base-02)",
          borderColor: "var(--base-04)",
        }}
      >
        <h3
          className="text-xs font-medium uppercase tracking-wide mb-3"
          style={{ color: "var(--text-tertiary)" }}
        >
          Recommended Actions
        </h3>
        <div className="animate-pulse space-y-2">
          <div
            className="h-8 rounded"
            style={{ background: "var(--base-03)" }}
          />
        </div>
      </div>
    );
  }

  // If no recommendations, provide defaults
  const actions =
    recommendations.length > 0
      ? recommendations
      : [
          "Initialize phase documentation",
          "Run preflight validation",
          "Create execution plan",
        ];

  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <h3
        className="text-xs font-medium uppercase tracking-wide mb-3"
        style={{ color: "var(--text-tertiary)" }}
      >
        Recommended Actions
      </h3>

      <div className="space-y-2">
        {actions.map((action, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 rounded border-l-2 transition-colors hover:bg-opacity-50 cursor-pointer"
            style={{
              background: "var(--base-01)",
              borderColor:
                index === 0 ? "var(--accent-primary)" : "var(--base-04)",
              borderLeftWidth: "2px",
              borderLeftStyle: "solid",
            }}
          >
            <div
              className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium"
              style={{
                background:
                  index === 0
                    ? "var(--accent-primary)"
                    : "var(--base-03)",
                color: index === 0 ? "white" : "var(--text-secondary)",
              }}
            >
              {index + 1}
            </div>
            <p
              className="text-sm flex-1"
              style={{ color: "var(--text-primary)" }}
            >
              {action}
            </p>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="mt-4 pt-4 border-t" style={{ borderColor: "var(--base-04)" }}>
        <h4
          className="text-xs font-medium mb-2"
          style={{ color: "var(--text-tertiary)" }}
        >
          Quick Links
        </h4>
        <div className="flex flex-wrap gap-2">
          <QuickLink label="Open Chat" icon="💬" />
          <QuickLink label="Open Shell" icon="💻" />
          <QuickLink label="Security Ops" icon="🛡️" />
        </div>
      </div>
    </div>
  );
}

function QuickLink({ label, icon }: { label: string; icon: string }) {
  return (
    <button
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors"
      style={{
        background: "var(--base-03)",
        color: "var(--text-secondary)",
      }}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </button>
  );
}
