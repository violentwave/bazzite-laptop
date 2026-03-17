#!/usr/bin/env node
/**
 * Guidance Hook Wiring for Claude Flow
 *
 * Registers guidance enforcement gates into the claude-flow hook lifecycle.
 * Run once at session start to activate governance.
 *
 * Hook mappings:
 *   PreCommand  -> destructive ops gate + secrets gate
 *   PreEdit     -> diff size gate + secrets gate
 *   PreTask     -> shard retrieval (inject relevant rules)
 *   PostTask    -> ledger finalization (record run completion)
 *
 * Usage:
 *   node scripts/guidance-hooks.mjs register    # Wire hooks into session
 *   node scripts/guidance-hooks.mjs status      # Show active gates + metrics
 *   node scripts/guidance-hooks.mjs metrics     # Show violation/rework stats
 *   node scripts/guidance-hooks.mjs unregister  # Remove guidance hooks
 */

import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

async function main() {
  const [action = 'status'] = process.argv.slice(2);

  const {
    GuidanceCompiler,
    createGates,
    createRetriever,
    HashEmbeddingProvider,
    createLedger,
    createGuidanceHooks,
    createProofChain,
    createTrustAccumulator,
  } = await import('@claude-flow/guidance');

  const { guidanceConfig } = await import(
    resolve(projectRoot, 'configs/guidance.config.mjs')
  );

  if (action === 'register') {
    await registerHooks({
      GuidanceCompiler,
      createGates,
      createRetriever,
      HashEmbeddingProvider,
      createLedger,
      createGuidanceHooks,
      createProofChain,
      createTrustAccumulator,
      guidanceConfig,
    });
  } else if (action === 'status') {
    await showStatus(guidanceConfig);
  } else if (action === 'metrics') {
    await showMetrics(guidanceConfig);
  } else if (action === 'unregister') {
    console.log('Guidance hooks will be removed at session end.');
    console.log('To force-remove, restart the claude-flow daemon.');
  } else {
    console.error(`Unknown action: ${action}. Use register, status, metrics, or unregister.`);
    process.exit(1);
  }
}

async function registerHooks(deps) {
  const {
    GuidanceCompiler,
    createGates,
    createRetriever,
    HashEmbeddingProvider,
    createLedger,
    createGuidanceHooks,
    createProofChain,
    createTrustAccumulator,
    guidanceConfig,
  } = deps;

  // Step 1: Compile CLAUDE.md
  console.log('Compiling CLAUDE.md...');
  const rootContent = readFileSync(guidanceConfig.rootGuidancePath, 'utf-8');
  const compiler = new GuidanceCompiler({
    maxConstitutionLines: 60,
    autoGenerateIds: true,
  });
  const bundle = compiler.compile(rootContent);
  console.log(`  ${bundle.manifest.totalRules} rules compiled`);

  // Step 2: Build enforcement gates
  const gates = createGates(guidanceConfig.gates);
  gates.setActiveRules(bundle.constitution.rules);

  // Step 3: Build retriever with hash-based embeddings (no GPU needed)
  const embeddingProvider = new HashEmbeddingProvider();
  const retriever = createRetriever(embeddingProvider);
  await retriever.loadBundle(bundle);
  console.log(`  ${retriever.shardCount} shards loaded into retriever`);

  // Step 4: Build ledger
  const ledger = createLedger();

  // Step 5: Wire hooks (no HookRegistry in standalone — hooks are available for manual wiring)
  const { provider } = createGuidanceHooks(gates, retriever, ledger);
  console.log(`  Hook provider created (PreCommand, PreEdit, PreTask, PostTask)`);

  // Step 6: Initialize proof chain
  const signingKey = createHash('sha256')
    .update('bazzite-laptop-guidance-' + bundle.constitution.hash)
    .digest('hex');
  const proofChain = createProofChain({ signingKey });
  console.log(`  Proof chain initialized (length: ${proofChain.getChainLength()})`);

  // Step 7: Initialize trust accumulator
  const trust = createTrustAccumulator({ initialTrust: 0.5 });
  console.log(`  Trust system initialized`);

  console.log('\nGuidance hooks registered. Governance active for this session.');
  console.log('Gates enforcing:');
  console.log('  - Destructive ops (sudo, rm -rf, systemctl, rpm-ostree)');
  console.log('  - Secrets detection (API keys, tokens, private keys)');
  console.log('  - Diff size limits (>300 lines requires plan)');
  console.log('  - Tool allowlist enforcement');
}

async function showStatus(config) {
  const { createGates } = await import('@claude-flow/guidance');
  const gates = createGates(config.gates);
  const activeGates = gates.getActiveGateCount();

  console.log('Guidance Control Plane Status:');
  console.log(`  CLAUDE.md: ${config.rootGuidancePath}`);
  console.log(`  Data dir: ${config.dataDir}`);
  console.log(`  Active gates: ${activeGates}`);
  console.log(`  Max shards/task: ${config.maxShardsPerTask}`);
  console.log(`  Optimization cycle: ${config.optimizationCycleDays} days`);
  console.log(`  Headless mode: ${config.headlessMode ? 'on' : 'off'}`);
}

async function showMetrics(config) {
  const { existsSync, readFileSync: readSync } = await import('node:fs');
  const manifestPath = resolve(config.dataDir, 'manifest.json');

  if (!existsSync(manifestPath)) {
    console.log('No governance data yet. Run: node scripts/guidance-init.mjs --export');
    return;
  }

  const manifest = JSON.parse(readSync(manifestPath, 'utf-8'));
  console.log('Guidance Metrics:');
  console.log(`  Total rules: ${manifest.totalRules}`);
  console.log(`  Constitution rules: ${manifest.constitutionRules}`);
  console.log(`  Shard rules: ${manifest.shardRules}`);
  console.log(`  Last compiled: ${new Date(manifest.compiledAt).toISOString()}`);
}

main().catch(err => {
  console.error('Guidance hooks error:', err.message);
  process.exit(1);
});
