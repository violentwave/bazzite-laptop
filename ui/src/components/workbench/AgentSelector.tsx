"use client";

import {
  WorkbenchAgentProfile,
  WorkbenchBackend,
  WorkbenchSandboxProfile,
} from "@/types/agent-workbench";

interface AgentSelectorProps {
  profiles: WorkbenchAgentProfile[];
  selectedBackend: WorkbenchBackend;
  selectedSandboxProfile: WorkbenchSandboxProfile;
  leaseMinutes: number;
  onBackendChange: (backend: WorkbenchBackend) => void;
  onSandboxChange: (profile: WorkbenchSandboxProfile) => void;
  onLeaseChange: (minutes: number) => void;
}

export function AgentSelector({
  profiles,
  selectedBackend,
  selectedSandboxProfile,
  leaseMinutes,
  onBackendChange,
  onSandboxChange,
  onLeaseChange,
}: AgentSelectorProps) {
  const selectedProfile = profiles.find((profile) => profile.id === selectedBackend) || profiles[0];

  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--base-02)", borderColor: "var(--base-04)" }}
    >
      <div>
        <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Agent Profile
        </h3>
        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
          Controlled backends with bounded capability constraints.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <label className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Backend
          <select
            value={selectedBackend}
            onChange={(event) => onBackendChange(event.target.value as WorkbenchBackend)}
            className="mt-1 w-full px-2 py-2 rounded-md text-sm"
            style={{
              background: "var(--base-01)",
              color: "var(--text-primary)",
              border: "1px solid var(--base-04)",
            }}
          >
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Sandbox
          <select
            value={selectedSandboxProfile}
            onChange={(event) => onSandboxChange(event.target.value as WorkbenchSandboxProfile)}
            className="mt-1 w-full px-2 py-2 rounded-md text-sm"
            style={{
              background: "var(--base-01)",
              color: "var(--text-primary)",
              border: "1px solid var(--base-04)",
            }}
          >
            <option value="conservative">conservative</option>
            <option value="analysis">analysis</option>
          </select>
        </label>

        <label className="text-xs" style={{ color: "var(--text-tertiary)" }}>
          Lease (minutes)
          <input
            type="number"
            min={1}
            max={1440}
            value={leaseMinutes}
            onChange={(event) => onLeaseChange(Number(event.target.value || 60))}
            className="mt-1 w-full px-2 py-2 rounded-md text-sm"
            style={{
              background: "var(--base-01)",
              color: "var(--text-primary)",
              border: "1px solid var(--base-04)",
            }}
          />
        </label>
      </div>

      {selectedProfile && (
        <div className="rounded-lg border p-3 text-xs" style={{ borderColor: "var(--base-04)" }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-medium" style={{ color: "var(--text-primary)" }}>
              {selectedProfile.label}
            </span>
            <span
              className="px-2 py-0.5 rounded-full"
              style={{ background: "var(--base-01)", color: "var(--accent-primary)" }}
            >
              {selectedProfile.mode}
            </span>
            <span
              className="px-2 py-0.5 rounded-full"
              style={{
                background: "var(--base-01)",
                color: selectedProfile.shell_access ? "var(--warning)" : "var(--success)",
              }}
            >
              shell {selectedProfile.shell_access ? "enabled" : "blocked"}
            </span>
            <span
              className="px-2 py-0.5 rounded-full"
              style={{
                background: "var(--base-01)",
                color: selectedProfile.network_access ? "var(--warning)" : "var(--success)",
              }}
            >
              network {selectedProfile.network_access ? "enabled" : "blocked"}
            </span>
          </div>
          <p className="mb-2" style={{ color: "var(--text-secondary)" }}>
            {selectedProfile.notes}
          </p>
          <div style={{ color: "var(--text-tertiary)" }}>
            Tools: {selectedProfile.allowed_tools.join(", ")}
          </div>
        </div>
      )}
    </div>
  );
}
