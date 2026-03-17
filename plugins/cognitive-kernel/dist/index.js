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
// Export types
export * from './types.js';
// Export MCP tools
export { workingMemoryTool, attentionControlTool, metaMonitorTool, scaffoldTool, cognitiveLoadTool, cognitiveKernelTools, toolHandlers, getTool, getToolNames, } from './mcp-tools.js';
// Export bridges
export { CognitiveBridge, createCognitiveBridge, SonaBridge, createSonaBridge, } from './bridges/index.js';
import { cognitiveKernelTools } from './mcp-tools.js';
import { createCognitiveBridge } from './bridges/cognitive-bridge.js';
import { createSonaBridge } from './bridges/sona-bridge.js';
/**
 * Cognitive Kernel Plugin metadata
 */
export const PLUGIN_METADATA = {
    name: '@claude-flow/plugin-cognitive-kernel',
    version: '3.0.0-alpha.1',
    description: 'Cognitive kernel plugin for LLM augmentation',
    author: 'Claude Flow Team',
    keywords: [
        'cognitive-kernel',
        'working-memory',
        'attention',
        'meta-cognition',
        'scaffolding',
        'sona',
        'cognitum',
    ],
};
let pluginState = {
    initialized: false,
    cognitiveBridge: null,
    sonaBridge: null,
};
/**
 * Initialize the cognitive kernel plugin
 */
export async function initializePlugin() {
    if (pluginState.initialized)
        return;
    // Initialize bridges
    pluginState.cognitiveBridge = createCognitiveBridge();
    pluginState.sonaBridge = createSonaBridge();
    await Promise.all([
        pluginState.cognitiveBridge.init(),
        pluginState.sonaBridge.init(),
    ]);
    pluginState.initialized = true;
}
/**
 * Shutdown the cognitive kernel plugin
 */
export async function shutdownPlugin() {
    if (!pluginState.initialized)
        return;
    await Promise.all([
        pluginState.cognitiveBridge?.destroy(),
        pluginState.sonaBridge?.destroy(),
    ]);
    pluginState = {
        initialized: false,
        cognitiveBridge: null,
        sonaBridge: null,
    };
}
/**
 * Get plugin state
 */
export function getPluginState() {
    return { ...pluginState };
}
/**
 * Get all MCP tools provided by this plugin
 */
export function getMCPTools() {
    return cognitiveKernelTools;
}
/**
 * Plugin interface for registration with Claude Flow
 */
export const cognitiveKernelPlugin = {
    metadata: PLUGIN_METADATA,
    state: 'uninitialized',
    async initialize() {
        this.state = 'initializing';
        try {
            await initializePlugin();
            this.state = 'ready';
        }
        catch (error) {
            this.state = 'error';
            throw error;
        }
    },
    async shutdown() {
        await shutdownPlugin();
        this.state = 'uninitialized';
    },
    getMCPTools() {
        return cognitiveKernelTools;
    },
    getAgentTypes() {
        return [
            'cognitive-controller',
            'working-memory-manager',
            'attention-director',
            'meta-cognitive-monitor',
            'scaffold-generator',
            'cognitive-load-optimizer',
        ];
    },
};
export default cognitiveKernelPlugin;
//# sourceMappingURL=index.js.map