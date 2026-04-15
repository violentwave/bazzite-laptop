"use client";

import { useState } from "react";

type ToolTab = "governance" | "discovery" | "marketplace" | "optimization" | "federation";

const tabs: { id: ToolTab; label: string; icon: React.ReactNode }[] = [
  {
    id: "governance",
    label: "Governance",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  {
    id: "discovery",
    label: "Discovery",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>
    ),
  },
  {
    id: "marketplace",
    label: "Marketplace",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="9" cy="21" r="1" />
        <circle cx="20" cy="21" r="1" />
        <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
      </svg>
    ),
  },
  {
    id: "optimization",
    label: "Optimization",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 20V10" />
        <path d="M18 20V4" />
        <path d="M6 20v-4" />
      </svg>
    ),
  },
  {
    id: "federation",
    label: "Federation",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
];

export function ToolControlCenterContainer() {
  const [activeTab, setActiveTab] = useState<ToolTab>("governance");

  return (
    <div className="h-full flex flex-col">
      {/* Tab Navigation */}
      <div
        className="flex border-b"
        style={{
          borderColor: "var(--base-04)",
          background: "var(--base-01)",
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm transition-colors ${
              activeTab === tab.id
                ? "border-b-2"
                : "hover:bg-base-02"
            }`}
            style={{
              color:
                activeTab === tab.id
                  ? "var(--accent-primary)"
                  : "var(--text-secondary)",
              borderColor:
                activeTab === tab.id ? "var(--accent-primary)" : "transparent",
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === "governance" && <GovernancePanel />}
        {activeTab === "discovery" && <DiscoveryPanel />}
        {activeTab === "marketplace" && <MarketplacePanel />}
        {activeTab === "optimization" && <OptimizationPanel />}
        {activeTab === "federation" && <FederationPanel />}
      </div>
    </div>
  );
}

function GovernancePanel() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="Total Tools" value="169" />
        <StatCard title="Active" value="165" status="success" />
        <StatCard title="Deprecated" value="4" status="warning" />
      </div>

      <SectionCard title="Tool Analytics" description="Usage statistics and trends">
        <div className="text-sm text-secondary">Analytics summary available via MCP tools</div>
      </SectionCard>

      <SectionCard title="Lifecycle Status" description="Tool versioning and deprecation">
        <div className="text-sm text-secondary">Lifecycle info available via MCP tools</div>
      </SectionCard>

      <SectionCard title="Policies & Audit" description="Governance policies and audit logs">
        <div className="text-sm text-secondary">Policy and audit data available via MCP tools</div>
      </SectionCard>
    </div>
  );
}

function DiscoveryPanel() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="Registered" value="169" />
        <StatCard title="Dynamic" value="12" status="success" />
        <StatCard title="Static" value="157" />
      </div>

      <SectionCard title="Registry Stats" description="Current tool registry status">
        <div className="text-sm text-secondary">Registry stats available via tool.registry_stats</div>
      </SectionCard>

      <SectionCard title="Discover Tools" description="Discover tools in Python modules">
        <div className="text-sm text-secondary">Use tool.discover to find tools in modules</div>
      </SectionCard>

      <SectionCard title="Reload & Watch" description="Hot-reload allowlist controls">
        <div className="text-sm text-secondary">Use tool.reload and tool.watch for dynamic updates</div>
      </SectionCard>
    </div>
  );
}

function MarketplacePanel() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="Available" value="0" />
        <StatCard title="Installed" value="0" />
        <StatCard title="Staged" value="0" />
      </div>

      <SectionCard title="Tool Packs" description="List and manage tool packs">
        <div className="text-sm text-secondary">Use tool.pack_list to view available packs</div>
      </SectionCard>

      <SectionCard title="Validate & Import" description="Validate and import tool packs">
        <div className="text-sm text-secondary">Use tool.pack_validate and tool.pack_import</div>
      </SectionCard>

      <SectionCard title="Export" description="Export tools to portable packs">
        <div className="text-sm text-secondary">Use tool.pack_export to create packs</div>
      </SectionCard>

      <SectionCard title="Install & Remove" description="Install or remove tool packs">
        <div className="text-sm text-secondary">Use tool.pack_install and tool.pack_remove</div>
      </SectionCard>
    </div>
  );
}

function OptimizationPanel() {
  return (
    <div className="space-y-6">
      <SectionCard title="Recommendations" description="Actionable optimization recommendations">
        <div className="text-sm text-secondary">Use tool.optimization.recommend</div>
      </SectionCard>

      <SectionCard title="Stale Tools" description="Detect unused and underutilized tools">
        <div className="text-sm text-secondary">Use tool.optimization.stale_tools</div>
      </SectionCard>

      <SectionCard title="Cost Report" description="Tool usage cost analysis">
        <div className="text-sm text-secondary">Use tool.optimization.cost_report</div>
      </SectionCard>

      <SectionCard title="Latency Report" description="Tool latency analysis">
        <div className="text-sm text-secondary">Use tool.optimization.latency_report</div>
      </SectionCard>

      <SectionCard title="Anomalies" description="Detect unusual tool usage patterns">
        <div className="text-sm text-secondary">Use tool.optimization.anomalies</div>
      </SectionCard>

      <SectionCard title="Forecast" description="Usage forecasting and trends">
        <div className="text-sm text-secondary">Use tool.optimization.forecast</div>
      </SectionCard>
    </div>
  );
}

function FederationPanel() {
  return (
    <div className="space-y-6">
      <SectionCard title="Discover Server" description="Discover external MCP servers">
        <div className="text-sm text-secondary">Use tool.federation.discover to find servers</div>
      </SectionCard>

      <SectionCard title="Server List" description="List discovered external servers">
        <div className="text-sm text-secondary">Use tool.federation.list_servers</div>
      </SectionCard>

      <SectionCard title="Inspect Server" description="Get external server details">
        <div className="text-sm text-secondary">Use tool.federation.inspect_server</div>
      </SectionCard>

      <SectionCard title="Trust Score" description="Calculate server trust scores">
        <div className="text-sm text-secondary">Use tool.federation.trust_score</div>
      </SectionCard>

      <SectionCard title="Audit Log" description="Federation action audit trail">
        <div className="text-sm text-secondary">Use tool.federation.audit</div>
      </SectionCard>

      <SectionCard title="Disable Server" description="Remove server from federation">
        <div className="text-sm text-secondary">Use tool.federation.disable (requires confirmation)</div>
      </SectionCard>
    </div>
  );
}

function StatCard({
  title,
  value,
  status,
}: {
  title: string;
  value: string;
  status?: "success" | "warning" | "danger";
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
        className="text-2xl font-semibold"
        style={{ color: status ? statusColors[status] : "var(--text-primary)" }}
      >
        {value}
      </div>
    </div>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="p-4 rounded-lg border"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="mb-2">
        <h3
          className="font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          {title}
        </h3>
        <p
          className="text-sm"
          style={{ color: "var(--text-tertiary)" }}
        >
          {description}
        </p>
      </div>
      <div style={{ color: "var(--text-secondary)" }}>{children}</div>
    </div>
  );
}
