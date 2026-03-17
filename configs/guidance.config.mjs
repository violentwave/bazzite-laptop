/**
 * Guidance Control Plane Configuration
 *
 * Maps CLAUDE.md rules to runtime enforcement gates, trust tiers,
 * and proof chain settings for the bazzite-laptop project.
 *
 * Usage:
 *   node scripts/guidance-init.mjs          # Compile + verify
 *   node scripts/guidance-check.mjs <cmd>   # Gate-check a command
 */

import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

/** @type {import('@claude-flow/guidance').GuidanceControlPlaneConfig} */
export const guidanceConfig = {
  rootGuidancePath: resolve(projectRoot, 'CLAUDE.md'),
  localGuidancePath: undefined,  // no CLAUDE.local.md yet
  dataDir: resolve(projectRoot, '.guidance'),
  maxShardsPerTask: 8,
  optimizationCycleDays: 7,
  headlessMode: false,
  gates: {
    destructiveOps: true,
    toolAllowlist: true,
    diffSize: true,
    secrets: true,
    diffSizeThreshold: 300,
    allowedTools: [
      'Read', 'Edit', 'Write', 'Glob', 'Grep', 'Bash',
      'Agent', 'Skill', 'ToolSearch',
    ],
    secretPatterns: [
      /(?:^|[^a-zA-Z0-9])(?:sk-|ghp_|gho_|glpat-|xoxb-|xoxp-|AKIA)[a-zA-Z0-9]{20,}/,
      /(?:API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)\s*[:=]\s*["'][^"']{8,}/i,
      /-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/,
      /(?:^|[^a-zA-Z0-9])eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}/,
    ],
    destructivePatterns: [
      /\bsudo\b/,
      /\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\b/,
      /\brm\s+-rf\b/,
      /\brpm-ostree\b/,
      /\bsystemctl\s+(enable|disable|start|stop|restart|mask)\b/,
      /\bgit\s+(push\s+--force|reset\s+--hard|clean\s+-[a-z]*f)\b/,
      /\bcurl\s+.*\|\s*(?:sudo\s+)?(?:bash|sh)\b/,
      /\bwget\s+.*-O\s*-\s*\|\s*(?:bash|sh)\b/,
    ],
  },
};

/** Custom gate rules derived from CLAUDE.md "NEVER violate" section */
export const aiLayerRules = [
  { id: 'AI-001', text: 'Never run local LLM generation models (only nomic-embed-text allowed)', riskClass: 'critical' },
  { id: 'AI-002', text: 'Never store API keys in code, scripts, or git', riskClass: 'critical' },
  { id: 'AI-003', text: 'Never install Python packages globally — use uv + .venv/', riskClass: 'high' },
  { id: 'AI-004', text: 'Never run AI as persistent daemons — on-demand only', riskClass: 'high' },
  { id: 'AI-005', text: 'Never call cloud APIs without ai/rate_limiter.py', riskClass: 'high' },
  { id: 'AI-006', text: 'Never hardcode API providers — use ai/router.py (LiteLLM)', riskClass: 'high' },
  { id: 'AI-007', text: 'Shell wrappers in scripts/, Python logic in ai/', riskClass: 'medium' },
  { id: 'AI-008', text: 'LanceDB at ~/security/vector-db/ — not in repo, not in /tmp', riskClass: 'medium' },
  { id: 'AI-009', text: 'Atomic writes for ~/security/.status — read-modify-write + tmp + mv', riskClass: 'medium' },
];

/** System-level rules from CLAUDE.md Rules section */
export const systemRules = [
  { id: 'SYS-001', text: 'Immutable OS — never modify /usr directly', riskClass: 'critical' },
  { id: 'SYS-002', text: 'Use rpm-ostree for system packages, flatpak for apps', riskClass: 'high' },
  { id: 'SYS-003', text: 'Never use sudo rm -rf, curl|bash, or wget without permission', riskClass: 'critical' },
  { id: 'SYS-004', text: 'Custom configs in /etc/ or ~/.config/ only', riskClass: 'medium' },
  { id: 'SYS-005', text: 'Test all changes before committing', riskClass: 'high' },
  { id: 'SYS-006', text: 'Never use PRIME offload env vars in game launch options', riskClass: 'high' },
  { id: 'SYS-007', text: 'Never lower vm.swappiness — 180 is correct for ZRAM', riskClass: 'high' },
];

/** Sandbox permission rules from CLAUDE.md */
export const sandboxRules = [
  { id: 'SBX-001', text: 'No sudo — no root commands', riskClass: 'critical' },
  { id: 'SBX-002', text: 'No systemctl enable/start/stop', riskClass: 'critical' },
  { id: 'SBX-003', text: 'No rpm-ostree — no system package management', riskClass: 'critical' },
  { id: 'SBX-004', text: 'No rm -rf — destructive deletion blocked', riskClass: 'critical' },
  { id: 'SBX-005', text: 'No reading .env, .key, .pem files', riskClass: 'critical' },
  { id: 'SBX-006', text: 'No writing to /usr/local/bin/ or /etc/', riskClass: 'critical' },
];

export default guidanceConfig;
