#!/usr/bin/env node
/**
 * Guidance Gate Checker
 *
 * Evaluates a command, tool use, or file edit against enforcement gates.
 * Designed to be called from claude-flow hooks (pre-command, pre-edit).
 *
 * Usage:
 *   node scripts/guidance-check.mjs command "sudo rm -rf /tmp"
 *   node scripts/guidance-check.mjs tool "Bash" '{"command":"sudo apt install"}'
 *   node scripts/guidance-check.mjs edit "ai/router.py" --diff-lines 500
 *   node scripts/guidance-check.mjs secrets "content to scan for secrets"
 *
 * Exit codes:
 *   0 = allowed
 *   1 = blocked
 *   2 = requires confirmation
 */

import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

/** Project sandbox hard-blocks from CLAUDE.md */
const SANDBOX_BLOCK_PATTERNS = [
  { pattern: /\bsudo\b/, rule: 'SBX-001', reason: 'sudo is blocked — no root access in sandbox' },
  { pattern: /\bsystemctl\s+(enable|disable|start|stop|restart|mask)\b/, rule: 'SBX-002', reason: 'systemctl is blocked — no service management' },
  { pattern: /\brpm-ostree\b/, rule: 'SBX-003', reason: 'rpm-ostree is blocked — no system package management' },
  { pattern: /\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)/, rule: 'SBX-004', reason: 'rm -rf is blocked — destructive deletion not allowed' },
  { pattern: /\bcurl\s+.*\|\s*(?:sudo\s+)?(?:bash|sh)\b/, rule: 'SYS-003', reason: 'curl|bash is blocked — no piped script execution' },
];

function applySandboxBlocks(command) {
  const blocks = [];
  for (const { pattern, rule, reason } of SANDBOX_BLOCK_PATTERNS) {
    if (pattern.test(command)) {
      blocks.push({ decision: 'block', gateName: 'sandbox-policy', reason, triggeredRules: [rule] });
    }
  }
  return blocks;
}

async function main() {
  const [mode, ...rest] = process.argv.slice(2);

  if (!mode || ['--help', '-h'].includes(mode)) {
    console.log('Usage: guidance-check.mjs <command|tool|edit|secrets> <args...>');
    process.exit(0);
  }

  const { createGates } = await import('@claude-flow/guidance');
  const { guidanceConfig } = await import(
    resolve(projectRoot, 'configs/guidance.config.mjs')
  );

  const gates = createGates(guidanceConfig.gates);
  let results;

  switch (mode) {
    case 'command': {
      const cmd = rest.join(' ');
      if (!cmd) { console.error('No command provided'); process.exit(1); }
      results = [...applySandboxBlocks(cmd), ...gates.evaluateCommand(cmd)];
      break;
    }
    case 'tool': {
      const [toolName, paramsJson] = rest;
      if (!toolName) { console.error('No tool name provided'); process.exit(1); }
      const params = paramsJson ? JSON.parse(paramsJson) : {};
      results = gates.evaluateToolUse(toolName, params);
      break;
    }
    case 'edit': {
      const filePath = rest[0];
      const diffIdx = rest.indexOf('--diff-lines');
      const diffLines = diffIdx >= 0 ? parseInt(rest[diffIdx + 1], 10) : 0;
      if (!filePath) { console.error('No file path provided'); process.exit(1); }
      results = gates.evaluateEdit(filePath, '', diffLines);
      break;
    }
    case 'secrets': {
      const content = rest.join(' ');
      const secretResult = gates.evaluateSecrets(content);
      results = secretResult ? [secretResult] : [];
      break;
    }
    default:
      console.error(`Unknown mode: ${mode}. Use command, tool, edit, or secrets.`);
      process.exit(1);
  }

  // Filter to non-allow results
  const issues = results.filter(r => r.decision !== 'allow');

  if (issues.length === 0) {
    console.log(JSON.stringify({ decision: 'allow', gates: results.length }));
    process.exit(0);
  }

  const hasBlock = issues.some(r => r.decision === 'block');
  const hasConfirm = issues.some(r => r.decision === 'require-confirmation');

  for (const issue of issues) {
    console.error(`[${issue.decision.toUpperCase()}] ${issue.gateName}: ${issue.reason}`);
    if (issue.remediation) {
      console.error(`  Remediation: ${issue.remediation}`);
    }
  }

  if (hasBlock) process.exit(1);
  if (hasConfirm) process.exit(2);
  process.exit(0);
}

main().catch(err => {
  console.error('Gate check failed:', err.message);
  process.exit(1);
});
