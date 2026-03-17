/**
 * Cognitive Kernel Plugin
 *
 * Cognitive augmentation for LLM reasoning with working memory,
 * attention control, meta-cognition, scaffolding, and cognitive load management.
 *
 * Features:
 * - Working memory slot management (Miller's 7 +/- 2)
 * - Attention control (focus, diffuse, selective, divided, sustained)
 * - Meta-cognitive monitoring and reflection
 * - Cognitive scaffolding (decomposition, analogy, Socratic, etc.)
 * - Cognitive load theory optimization
 * - SONA integration for continuous learning
 *
 * @packageDocumentation
 */
export * from './types.js';
export { workingMemoryTool, attentionControlTool, metaMonitorTool, scaffoldTool, cognitiveLoadTool, cognitiveKernelTools, toolHandlers, getTool, getToolNames, } from './mcp-tools.js';
export { CognitiveBridge, createCognitiveBridge, SonaBridge, createSonaBridge, } from './bridges/index.js';
export type { CognitiveConfig, AttentionState, } from './bridges/cognitive-bridge.js';
export type { SonaConfig, SonaTrajectory, SonaStep, LoRAWeights, EWCState, SonaPrediction, } from './bridges/sona-bridge.js';
import type { MCPTool } from './types.js';
import { CognitiveBridge } from './bridges/cognitive-bridge.js';
import { SonaBridge } from './bridges/sona-bridge.js';
/**
 * Cognitive Kernel Plugin metadata
 */
export declare const PLUGIN_METADATA: {
    readonly name: "@claude-flow/plugin-cognitive-kernel";
    readonly version: "3.0.0-alpha.1";
    readonly description: "Cognitive kernel plugin for LLM augmentation";
    readonly author: "Claude Flow Team";
    readonly keywords: readonly ["cognitive-kernel", "working-memory", "attention", "meta-cognition", "scaffolding", "sona", "cognitum"];
};
/**
 * Plugin state
 */
export interface CognitiveKernelPluginState {
    initialized: boolean;
    cognitiveBridge: CognitiveBridge | null;
    sonaBridge: SonaBridge | null;
}
/**
 * Initialize the cognitive kernel plugin
 */
export declare function initializePlugin(): Promise<void>;
/**
 * Shutdown the cognitive kernel plugin
 */
export declare function shutdownPlugin(): Promise<void>;
/**
 * Get plugin state
 */
export declare function getPluginState(): CognitiveKernelPluginState;
/**
 * Get all MCP tools provided by this plugin
 */
export declare function getMCPTools(): MCPTool[];
/**
 * Plugin interface for registration with Claude Flow
 */
export declare const cognitiveKernelPlugin: {
    metadata: {
        readonly name: "@claude-flow/plugin-cognitive-kernel";
        readonly version: "3.0.0-alpha.1";
        readonly description: "Cognitive kernel plugin for LLM augmentation";
        readonly author: "Claude Flow Team";
        readonly keywords: readonly ["cognitive-kernel", "working-memory", "attention", "meta-cognition", "scaffolding", "sona", "cognitum"];
    };
    state: "uninitialized" | "initializing" | "ready" | "error";
    initialize(): Promise<void>;
    shutdown(): Promise<void>;
    getMCPTools(): MCPTool[];
    getAgentTypes(): string[];
};
export default cognitiveKernelPlugin;
//# sourceMappingURL=index.d.ts.map