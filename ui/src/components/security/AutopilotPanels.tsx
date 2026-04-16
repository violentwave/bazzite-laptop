"use client";

import {
  AutopilotAuditEvent,
  AutopilotEvidenceBundle,
  AutopilotFinding,
  AutopilotIncident,
  AutopilotOverview,
  AutopilotPolicyStatus,
  AutopilotQueueItem,
} from "@/types/security-autopilot";

interface OverviewPanelProps {
  overview: AutopilotOverview | null;
}

interface FindingsPanelProps {
  findings: AutopilotFinding[];
}

interface IncidentsPanelProps {
  incidents: AutopilotIncident[];
}

interface EvidencePanelProps {
  bundles: AutopilotEvidenceBundle[];
}

interface AuditPanelProps {
  events: AutopilotAuditEvent[];
}

interface PolicyPanelProps {
  policy: AutopilotPolicyStatus | null;
}

interface RemediationQueuePanelProps {
  queue: AutopilotQueueItem[];
}

function formatTime(value?: string | null): string {
  if (!value) return "Unknown";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function severityColor(severity: string): string {
  if (severity === "critical") return "var(--danger)";
  if (severity === "high") return "var(--warning)";
  if (severity === "medium") return "var(--accent-primary)";
  if (severity === "low") return "var(--success)";
  return "var(--text-secondary)";
}

function SurfaceCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-xl border p-5"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="mb-4">
        <h3 className="text-lg font-medium" style={{ color: "var(--text-primary)" }}>
          {title}
        </h3>
        {subtitle && (
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div
      className="rounded-xl border p-8 text-center"
      style={{
        background: "var(--base-02)",
        borderColor: "var(--base-04)",
      }}
    >
      <p style={{ color: "var(--text-secondary)" }}>{message}</p>
    </div>
  );
}

export function AutopilotOverviewPanel({ overview }: OverviewPanelProps) {
  if (!overview) {
    return <EmptyState message="Autopilot overview unavailable. Retry after MCP refresh." />;
  }

  return (
    <div className="space-y-5">
      <SurfaceCard
        title="Security Autopilot Overview"
        subtitle={`Policy ${overview.policy_version} · default mode ${overview.default_mode}`}
      >
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Metric label="Findings" value={overview.finding_count.toString()} />
          <Metric label="Incidents" value={overview.incident_count.toString()} />
          <Metric label="Queue" value={overview.remediation_queue_count.toString()} />
          <Metric label="Audit Events" value={overview.audit_event_count.toString()} />
        </div>
      </SurfaceCard>

      <SurfaceCard title="Risk Posture">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <Metric label="Critical" value={String(overview.severity_counts.critical)} emphasize="critical" />
          <Metric label="High" value={String(overview.severity_counts.high)} emphasize="high" />
          <Metric label="Medium" value={String(overview.severity_counts.medium)} emphasize="medium" />
          <Metric label="Low" value={String(overview.severity_counts.low)} emphasize="low" />
          <Metric label="Blocked Actions" value={String(overview.blocked_action_count)} emphasize="critical" />
        </div>
      </SurfaceCard>

      <SurfaceCard title="Top Categories" subtitle={`Last scan: ${formatTime(overview.last_scan_time)}`}>
        <div className="space-y-2">
          {overview.top_categories.length === 0 && (
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              No categorized findings available.
            </p>
          )}
          {overview.top_categories.map((item) => (
            <div key={item.category} className="flex items-center justify-between text-sm">
              <span style={{ color: "var(--text-secondary)" }}>{item.category}</span>
              <span style={{ color: "var(--text-primary)" }}>{item.count}</span>
            </div>
          ))}
        </div>
      </SurfaceCard>
    </div>
  );
}

function Metric({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: string;
  emphasize?: string;
}) {
  return (
    <div
      className="rounded-lg border p-3"
      style={{
        background: "var(--base-01)",
        borderColor: "var(--base-04)",
      }}
    >
      <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>
        {label}
      </div>
      <div
        className="text-xl font-semibold mt-1"
        style={{ color: emphasize ? severityColor(emphasize) : "var(--text-primary)" }}
      >
        {value}
      </div>
    </div>
  );
}

export function AutopilotFindingsPanel({ findings }: FindingsPanelProps) {
  if (findings.length === 0) {
    return <EmptyState message="No autopilot findings available right now." />;
  }

  return (
    <div className="space-y-3">
      {findings.map((finding) => (
        <div
          key={finding.finding_id}
          className="rounded-lg border p-4"
          style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
        >
          <div className="flex items-center justify-between gap-3">
            <h4 className="font-medium" style={{ color: "var(--text-primary)" }}>
              {finding.title}
            </h4>
            <span
              className="text-xs px-2 py-1 rounded-full"
              style={{
                background: `${severityColor(finding.severity)}22`,
                color: severityColor(finding.severity),
              }}
            >
              {finding.severity}
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {finding.description}
          </p>
          <div className="text-xs mt-3" style={{ color: "var(--text-tertiary)" }}>
            {finding.category} · {finding.source} · {formatTime(finding.detected_at)}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AutopilotIncidentsPanel({ incidents }: IncidentsPanelProps) {
  if (incidents.length === 0) {
    return <EmptyState message="No incidents are currently grouped by autopilot." />;
  }

  return (
    <div className="space-y-3">
      {incidents.map((incident) => (
        <div
          key={incident.incident_id}
          className="rounded-lg border p-4"
          style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
        >
          <div className="flex items-center justify-between">
            <h4 className="font-medium" style={{ color: "var(--text-primary)" }}>
              {incident.title}
            </h4>
            <span style={{ color: severityColor(incident.severity) }} className="text-sm font-medium">
              {incident.severity}
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {incident.summary}
          </p>
          <div className="text-xs mt-3" style={{ color: "var(--text-tertiary)" }}>
            status={incident.status} · findings={incident.finding_count} · updated={formatTime(incident.updated_at)}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AutopilotEvidencePanel({ bundles }: EvidencePanelProps) {
  if (bundles.length === 0) {
    return <EmptyState message="No redacted evidence bundles available." />;
  }

  return (
    <div className="space-y-3">
      {bundles.map((bundle) => (
        <SurfaceCard
          key={bundle.bundle_id}
          title={bundle.bundle_id}
          subtitle={`${bundle.source} · redactions=${bundle.redaction_count} · ${formatTime(bundle.created_at)}`}
        >
          <div className="space-y-2">
            {bundle.items.slice(0, 3).map((item) => (
              <div key={item.item_id} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--text-primary)" }}>{item.key}:</span>{" "}
                {typeof item.value === "string" ? item.value : JSON.stringify(item.value)}
              </div>
            ))}
          </div>
        </SurfaceCard>
      ))}
    </div>
  );
}

export function AutopilotAuditPanel({ events }: AuditPanelProps) {
  if (events.length === 0) {
    return <EmptyState message="No autopilot audit events were found in the ledger." />;
  }

  return (
    <div className="space-y-2">
      {events.map((event, index) => (
        <div
          key={`${event.event_hash || "event"}-${index}`}
          className="rounded-lg border p-3"
          style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
        >
          <div className="flex items-center justify-between text-sm">
            <span style={{ color: "var(--text-primary)" }}>{event.event_type || "unknown"}</span>
            <span style={{ color: "var(--text-tertiary)" }}>{formatTime(event.created_at)}</span>
          </div>
          <div className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
            actor={event.actor || "unknown"} · incident={event.incident_id || "n/a"}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AutopilotPolicyPanel({ policy }: PolicyPanelProps) {
  if (!policy) {
    return <EmptyState message="Policy status unavailable." />;
  }

  return (
    <div className="space-y-5">
      <SurfaceCard title="Policy Status" subtitle={`version ${policy.policy_version}`}>
        <div className="space-y-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          <div>Default mode: {policy.default_mode}</div>
          <div>Modes: {policy.mode_names.join(", ")}</div>
        </div>
      </SurfaceCard>

      <SurfaceCard title="Always Blocked Categories">
        <ListTokens values={policy.blocked_always} color="var(--danger)" />
      </SurfaceCard>

      <SurfaceCard title="Destructive Categories">
        <ListTokens values={policy.destructive_actions} color="var(--warning)" />
      </SurfaceCard>

      <SurfaceCard title="Allowed Path Prefixes">
        <div className="space-y-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          {policy.allowed_path_prefixes.map((prefix) => (
            <div key={prefix}>{prefix}</div>
          ))}
        </div>
      </SurfaceCard>
    </div>
  );
}

function ListTokens({ values, color }: { values: string[]; color: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value) => (
        <span
          key={value}
          className="text-xs px-2 py-1 rounded-full"
          style={{ background: `${color}1f`, color }}
        >
          {value}
        </span>
      ))}
    </div>
  );
}

export function AutopilotRemediationQueuePanel({ queue }: RemediationQueuePanelProps) {
  if (queue.length === 0) {
    return <EmptyState message="No plan-only remediation entries are queued." />;
  }

  return (
    <div className="space-y-3">
      {queue.map((item) => (
        <div
          key={item.plan_id}
          className="rounded-lg border p-4"
          style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
        >
          <div className="flex items-center justify-between">
            <h4 className="font-medium" style={{ color: "var(--text-primary)" }}>
              {item.incident_title}
            </h4>
            <span style={{ color: severityColor(item.priority) }} className="text-sm font-medium">
              {item.priority}
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {item.summary}
          </p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mt-3 text-xs" style={{ color: "var(--text-tertiary)" }}>
            <div>actions={item.action_count}</div>
            <div>requires_approval={item.requires_approval ? "yes" : "no"}</div>
            <div>blocked={item.blocked_actions}</div>
            <div>auto_allowed={item.auto_allowed_actions}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
