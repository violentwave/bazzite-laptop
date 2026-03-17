/**
 * Agentic-QE Plugin Implementation
 * Main plugin class implementing PluginInterface with lifecycle methods
 *
 * @module v3/plugins/agentic-qe/plugin
 * @version 3.2.3
 */
import type { BoundedContext, ModelTier } from './types.js';
/**
 * Plugin interface for V3 plugin system
 */
interface IPlugin {
    readonly name: string;
    readonly version: string;
    readonly description: string;
    readonly author: string;
    readonly capabilities: readonly string[];
    register(registry: IPluginRegistry): Promise<void>;
    initialize(context: IPluginContext): Promise<void>;
    shutdown(): Promise<void>;
    getHealth(): Promise<PluginHealthStatus>;
}
/**
 * Plugin registry for tool/hook/worker registration
 */
interface IPluginRegistry {
    registerTool?(tool: IMCPTool): void;
    registerHook?(hook: QEHookDefinition): void;
    registerWorker?(worker: QEWorkerDefinition): void;
    registerAgent?(agent: QEAgentDefinition): void;
    registerTools?(tools: IMCPTool[]): void;
    registerHooks?(hooks: QEHookDefinition[]): void;
    registerWorkers?(workers: QEWorkerDefinition[]): void;
    registerAgents?(agents: QEAgentDefinition[]): void;
}
/**
 * Plugin context with V3 services
 */
interface IPluginContext {
    services: {
        memory?: unknown;
        security?: unknown;
        embeddings?: unknown;
        modelRouter?: unknown;
        hiveMind?: unknown;
        ui?: unknown;
    };
    config: Record<string, unknown>;
    logger: {
        debug(message: string, ...args: unknown[]): void;
        info(message: string, ...args: unknown[]): void;
        warn(message: string, ...args: unknown[]): void;
        error(message: string, ...args: unknown[]): void;
    };
    getConfig?(): Record<string, unknown>;
    set?(key: string, value: unknown): void;
    getMemoryService?(): {
        clearNamespace(ns: string): Promise<void>;
        createNamespace?(config: unknown): Promise<void>;
    } | null;
    getSecurityModule?(): {
        pathValidator: {
            validate(path: string): Promise<{
                valid: boolean;
                error?: string;
            }>;
        };
    } | null;
    getUIService?(): {
        confirm(message: string): Promise<boolean>;
    } | null;
}
/**
 * MCP tool interface
 */
interface IMCPTool {
    name: string;
    description: string;
    inputSchema: Record<string, unknown>;
    category?: string;
    version?: string;
    handler?: (input: unknown, context: IPluginContext) => Promise<MCPToolResult>;
    execute?: (input: unknown, context: IPluginContext) => Promise<MCPToolResult>;
}
/**
 * MCP tool result
 */
interface MCPToolResult {
    content?: Array<{
        type: string;
        text: string;
    }>;
    success?: boolean;
    data?: unknown;
    error?: string;
    isError?: boolean;
}
/**
 * Plugin health status
 */
interface PluginHealthStatus {
    healthy: boolean;
    status?: 'healthy' | 'degraded' | 'unhealthy';
    components: Record<string, ComponentHealth>;
    lastCheck: number;
    uptime: number;
}
/**
 * Component health
 */
interface ComponentHealth {
    name: string;
    healthy: boolean;
    status?: 'healthy' | 'degraded' | 'unhealthy';
    message?: string;
    lastCheck: number;
    lastSuccess?: number;
}
/**
 * Hook definition
 */
interface QEHookDefinition {
    name: string;
    event: string;
    priority: 'low' | 'normal' | 'high' | 'critical';
    description?: string;
    handler: string | ((context: IPluginContext, data: unknown) => Promise<void>);
}
/**
 * Worker definition
 */
interface QEWorkerDefinition {
    name: string;
    type: string;
    capabilities?: string[];
    maxConcurrent?: number;
    handler?: (context: IPluginContext, input: unknown) => Promise<unknown>;
}
/**
 * Agent definition
 */
interface QEAgentDefinition {
    id: string;
    name?: string;
    type?: string;
    context: string | BoundedContext;
    capabilities: string[];
    modelTier?: ModelTier;
    description?: string;
}
/**
 * Main Agentic-QE Plugin class
 * Implements IPlugin interface for claude-flow integration
 */
export declare class AQEPlugin implements IPlugin {
    readonly name = "agentic-qe";
    readonly version = "3.2.3";
    readonly description = "Quality Engineering plugin with 51 specialized agents across 12 DDD bounded contexts";
    readonly author = "rUv";
    readonly capabilities: ("test-generation" | "test-execution" | "coverage-analysis" | "quality-assessment" | "defect-intelligence" | "requirements-validation" | "code-intelligence" | "security-compliance" | "contract-testing" | "visual-accessibility" | "chaos-resilience" | "learning-optimization")[];
    private config;
    private context;
    private contextMapper;
    private sandbox;
    private initialized;
    private componentHealth;
    /**
     * Register the plugin with the plugin system
     */
    register(registry: IPluginRegistry): Promise<void>;
    /**
     * Initialize the plugin with context
     */
    initialize(context: IPluginContext): Promise<void>;
    /**
     * Shutdown the plugin cleanly
     */
    shutdown(): Promise<void>;
    /**
     * Get plugin health status
     */
    getHealth(): Promise<PluginHealthStatus>;
    private updateHealth;
    private initializeMemoryNamespaces;
    private getMCPTools;
    private getHooks;
    private getWorkers;
    private getAgents;
    private getModelTierForSecurityLevel;
    private handleGenerateTests;
    private handleAnalyzeCoverage;
    private handleSecurityScan;
    private handleEvaluateQualityGate;
    private handlePredictDefects;
    private handleValidateContract;
    private handleChaosInject;
    private handleTDDCycle;
}
export {};
//# sourceMappingURL=plugin.d.ts.map