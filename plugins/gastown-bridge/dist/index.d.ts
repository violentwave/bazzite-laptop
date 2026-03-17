/**
 * Gas Town Bridge Plugin - Main Entry Point
 *
 * GasTownBridgePlugin class implementing the IPlugin interface:
 * - register(): Register with claude-flow plugin system
 * - initialize(): Load WASM modules, set up bridges
 * - shutdown(): Cleanup resources
 *
 * Provides integration with Steve Yegge's Gas Town orchestrator:
 * - Beads: Git-backed issue tracking with graph semantics
 * - Formulas: TOML-defined workflows (convoy, workflow, expansion, aspect)
 * - Convoys: Work-order tracking for slung work
 * - WASM: 352x faster formula parsing and graph analysis
 *
 * @module gastown-bridge
 * @version 0.1.0
 */
import { EventEmitter } from 'events';
import type { Bead, Formula, GasTownConfig, CreateBeadOptions, SlingOptions, SyncResult, TopoSortResult, CriticalPathResult, BeadGraph } from './types.js';
import { GtBridge } from './bridges/gt-bridge.js';
import { BdBridge } from './bridges/bd-bridge.js';
import { SyncBridge } from './bridges/sync-bridge.js';
import { FormulaExecutor } from './formula/executor.js';
import { ConvoyTracker } from './convoy/tracker.js';
import { ConvoyObserver } from './convoy/observer.js';
/**
 * Plugin context interface
 */
export interface PluginContext {
    get<T>(key: string): T;
    set<T>(key: string, value: T): void;
    has(key: string): boolean;
}
/**
 * MCP Tool definition for plugin interface
 */
export interface PluginMCPTool {
    name: string;
    description: string;
    category: string;
    version: string;
    inputSchema: {
        type: 'object';
        properties: Record<string, unknown>;
        required?: string[];
    };
    handler: (input: unknown, context: PluginContext) => Promise<{
        content: Array<{
            type: 'text';
            text: string;
        }>;
    }>;
}
/**
 * Hook priority type
 */
export type HookPriority = number;
/**
 * Plugin hook definition
 */
export interface PluginHook {
    name: string;
    event: string;
    priority: HookPriority;
    description: string;
    handler: (context: PluginContext, payload: unknown) => Promise<unknown>;
}
/**
 * Plugin interface
 */
export interface IPlugin {
    readonly name: string;
    readonly version: string;
    readonly description: string;
    register(context: PluginContext): Promise<void>;
    initialize(context: PluginContext): Promise<{
        success: boolean;
        error?: string;
    }>;
    shutdown(context: PluginContext): Promise<{
        success: boolean;
        error?: string;
    }>;
    getCapabilities(): string[];
    getMCPTools(): PluginMCPTool[];
    getHooks(): PluginHook[];
}
/**
 * Gas Town CLI bridge interface
 */
export interface IGasTownBridge {
    gt(args: string[]): Promise<string>;
    bd(args: string[]): Promise<string>;
    createBead(opts: CreateBeadOptions): Promise<Bead>;
    getReady(limit?: number, rig?: string): Promise<Bead[]>;
    showBead(beadId: string): Promise<Bead>;
    addDep(child: string, parent: string): Promise<void>;
    removeDep(child: string, parent: string): Promise<void>;
    sling(opts: SlingOptions): Promise<void>;
}
/**
 * Formula engine interface
 */
export interface IFormulaEngine {
    parse(content: string): Formula;
    cook(formula: Formula, vars: Record<string, string>): Formula;
    toMolecule(formula: Formula, bridge: IGasTownBridge): Promise<string[]>;
}
/**
 * WASM bridge interface
 */
export interface IWasmBridge {
    initialize(): Promise<void>;
    isInitialized(): boolean;
    dispose(): Promise<void>;
    parseFormula(content: string): Formula;
    cookFormula(formula: Formula, vars: Record<string, string>): Formula;
    resolveDeps(beads: Bead[]): TopoSortResult;
    detectCycle(graph: BeadGraph): boolean;
    criticalPath(beads: Bead[], durations: Map<string, number>): CriticalPathResult;
    batchCook(formulas: Formula[], vars: Record<string, string>[]): Formula[];
}
/**
 * Sync service interface
 */
export interface ISyncService {
    pullBeads(rig?: string): Promise<number>;
    pushTasks(namespace: string): Promise<number>;
    sync(direction: 'pull' | 'push' | 'both', rig?: string): Promise<SyncResult>;
}
/**
 * Gas Town Bridge Plugin configuration
 */
export interface GasTownBridgeConfig {
    /** Base Gas Town configuration */
    gastown: Partial<GasTownConfig>;
    /** GtBridge configuration */
    gtBridge?: {
        /** Path to gt CLI binary */
        gtPath?: string;
        /** CLI execution timeout in ms */
        timeout?: number;
        /** Working directory */
        cwd?: string;
    };
    /** BdBridge configuration */
    bdBridge?: {
        /** Path to bd CLI binary */
        bdPath?: string;
        /** CLI execution timeout in ms */
        timeout?: number;
        /** Working directory */
        cwd?: string;
    };
    /** SyncBridge configuration */
    syncBridge?: {
        /** AgentDB namespace for beads */
        namespace?: string;
        /** Sync interval in ms */
        syncInterval?: number;
        /** Enable auto-sync */
        autoSync?: boolean;
    };
    /** FormulaExecutor configuration */
    formulaExecutor?: {
        /** Enable WASM acceleration */
        useWasm?: boolean;
        /** Step execution timeout in ms */
        stepTimeout?: number;
        /** Maximum parallel steps */
        maxParallel?: number;
    };
    /** ConvoyTracker configuration */
    convoyTracker?: {
        /** Auto-update progress on issue changes */
        autoUpdateProgress?: boolean;
        /** Progress update interval in ms */
        progressUpdateInterval?: number;
        /** Enable persistent storage */
        persistConvoys?: boolean;
        /** Storage path for convoy data */
        storagePath?: string;
    };
    /** ConvoyObserver configuration */
    convoyObserver?: {
        /** Polling interval in ms */
        pollInterval?: number;
        /** Maximum poll attempts (0 = unlimited) */
        maxPollAttempts?: number;
        /** Enable WASM for graph analysis */
        useWasm?: boolean;
    };
    /** WASM configuration */
    wasm?: {
        /** Enable WASM acceleration */
        enabled?: boolean;
        /** Preload WASM modules on init */
        preload?: boolean;
    };
    /** GUPP (Git Universal Pull/Push) adapter configuration */
    gupp?: {
        /** Enable GUPP adapter */
        enabled?: boolean;
        /** GUPP endpoint URL */
        endpoint?: string;
        /** Authentication token */
        authToken?: string;
    };
    /** Logger configuration */
    logger?: {
        /** Log level */
        level?: 'debug' | 'info' | 'warn' | 'error';
        /** Enable structured logging */
        structured?: boolean;
    };
}
/**
 * GUPP (Git Universal Pull/Push) Adapter
 *
 * Provides integration with external Git services for cross-repository
 * bead synchronization. This is a stub implementation - full implementation
 * would connect to GUPP services.
 */
export interface IGuppAdapter {
    /** Check if GUPP is available */
    isAvailable(): boolean;
    /** Pull beads from remote */
    pull(options?: {
        rig?: string;
        since?: Date;
    }): Promise<Bead[]>;
    /** Push beads to remote */
    push(beads: Bead[]): Promise<{
        pushed: number;
        errors: string[];
    }>;
    /** Sync with remote */
    sync(): Promise<{
        pulled: number;
        pushed: number;
        conflicts: string[];
    }>;
}
/**
 * Gas Town Bridge Plugin for Claude Flow V3
 *
 * Provides integration with Gas Town orchestrator:
 * - 5 Beads MCP tools (CLI-based)
 * - 3 Convoy MCP tools
 * - 4 Formula MCP tools (WASM-accelerated)
 * - 5 WASM computation tools
 * - 3 Orchestration tools
 */
export declare class GasTownBridgePlugin extends EventEmitter implements IPlugin {
    readonly name = "@claude-flow/plugin-gastown-bridge";
    readonly version = "0.1.0";
    readonly description = "Gas Town orchestrator integration with WASM-accelerated formula parsing and graph analysis";
    private config;
    private pluginContext;
    private logger;
    private gtBridge;
    private bdBridge;
    private syncBridge;
    private formulaExecutor;
    private convoyTracker;
    private convoyObserver;
    private wasmLoader;
    private guppAdapter;
    private wasmInitialized;
    private cliAvailable;
    private initialized;
    constructor(config?: Partial<GasTownBridgeConfig>);
    /**
     * Register the plugin with claude-flow
     */
    register(context: PluginContext): Promise<void>;
    /**
     * Initialize the plugin (load WASM, set up bridges)
     */
    initialize(context: PluginContext): Promise<{
        success: boolean;
        error?: string;
    }>;
    /**
     * Shutdown the plugin (cleanup resources)
     */
    shutdown(_context: PluginContext): Promise<{
        success: boolean;
        error?: string;
    }>;
    /**
     * Get plugin capabilities
     */
    getCapabilities(): string[];
    /**
     * Get plugin MCP tools
     */
    getMCPTools(): PluginMCPTool[];
    /**
     * Get plugin hooks
     */
    getHooks(): PluginHook[];
    /**
     * Get the current configuration
     */
    getConfig(): GasTownBridgeConfig;
    /**
     * Update configuration
     */
    updateConfig(config: Partial<GasTownBridgeConfig>): void;
    /**
     * Check if WASM is initialized
     */
    isWasmReady(): boolean;
    /**
     * Check if CLI tools are available
     */
    isCliAvailable(): boolean;
    /**
     * Get bridge instances
     */
    getBridges(): {
        gt: GtBridge | null;
        bd: BdBridge | null;
        sync: SyncBridge | null;
    };
    /**
     * Get formula executor
     */
    getFormulaExecutor(): FormulaExecutor | null;
    /**
     * Get convoy tracker
     */
    getConvoyTracker(): ConvoyTracker | null;
    /**
     * Get convoy observer
     */
    getConvoyObserver(): ConvoyObserver | null;
    /**
     * Get GUPP adapter
     */
    getGuppAdapter(): IGuppAdapter | null;
    /**
     * Get plugin metadata
     */
    getMetadata(): {
        name: string;
        version: string;
        description: string;
        author: string;
        license: string;
        repository: string;
        keywords: string[];
        mcpTools: string[];
        capabilities: string[];
    };
    private mergeConfig;
    private initializeWasm;
    private checkCliAvailable;
    private initializeBridges;
    private initializeFormulaExecutor;
    private initializeConvoyComponents;
    private initializeGuppAdapter;
    /**
     * Create a stub AgentDB service for SyncBridge initialization.
     * This stub stores data in-memory and should be replaced with
     * the real AgentDB service from the plugin context.
     */
    private createStubAgentDB;
    private convertMcpTool;
    private zodToJsonSchema;
    private createToolContext;
    /**
     * Create the bridge facade for MCP tools.
     *
     * NOTE: This facade bridges between the plugin's internal types (from bd-bridge, etc.)
     * and the external interface types (from types.ts). Type casts are necessary because
     * the underlying bridges use different type definitions. A future refactor should
     * unify these type systems.
     */
    private createBridgeFacade;
    private createSyncFacade;
    private createFormulaWasmFacade;
    private createDependencyWasmFacade;
    private simpleSimilarity;
    private createPreTaskHook;
    private createPostTaskHook;
    private createBeadsSyncHook;
    private createConvoyProgressHook;
}
/**
 * Create a new Gas Town Bridge Plugin instance
 */
export declare function createGasTownBridgePlugin(config?: Partial<GasTownBridgeConfig>): GasTownBridgePlugin;
export * from './types.js';
export * from './bridges/index.js';
export * from './convoy/index.js';
export { FormulaExecutor, createFormulaExecutor, type IWasmLoader, type ExecuteOptions, type StepContext, type StepResult, type Molecule, type ExecutionProgress, type ExecutorEvents, } from './formula/executor.js';
export { gasTownBridgeTools, toolHandlers, toolCategories, getTool, getToolsByLayer, type MCPTool, type ToolContext, type MCPToolResult, } from './mcp-tools.js';
export { isWasmAvailable, loadFormulaWasm, parseFormula, cookFormula, cookBatch, loadGnnWasm, topoSort, detectCycles, criticalPath, preloadWasmModules, getWasmVersions, resetWasmCache, getPerformanceLog, clearPerformanceLog, type PerformanceTiming, type GraphEdge, type NodeWeight, type CycleDetectionResult, default as WasmLoader, } from './wasm-loader.js';
export { GasTownError, BeadsError, ValidationError, CLIExecutionError, FormulaError, ConvoyError, GasTownErrorCode as ErrorCodes, type GasTownErrorCodeType, type ValidationConstraint, isGasTownError, isValidationError, isCLIExecutionError, isBeadsError, wrapError, getErrorMessage, } from './errors.js';
export { validateBeadId, validateFormulaName, validateConvoyId, validateGtArgs, validateCreateBeadOptions as validateBeadOptions, validateCreateConvoyOptions as validateConvoyOptions, validateSlingOptions as validateSling, BeadIdSchema as BeadIdValidationSchema, FormulaNameSchema, ConvoyIdSchema, GtArgsSchema, SafeStringSchema as ValidatorSafeStringSchema, RigNameSchema, PrioritySchema, LabelsSchema, containsShellMetacharacters, containsPathTraversal, isSafeArgument, isValidBeadId, isValidFormulaName, isValidConvoyId, MAX_LENGTHS, SHELL_METACHARACTERS, PATH_TRAVERSAL_PATTERNS, BEAD_ID_PATTERN, FORMULA_NAME_PATTERN, UUID_PATTERN, CONVOY_HASH_PATTERN, } from './validators.js';
export { sanitizeBeadOutput, sanitizeFormulaOutput, sanitizeConvoyOutput, sanitizeBeadsListOutput, MAX_OUTPUT_SIZE, SENSITIVE_FIELD_PATTERNS, REDACTED_FIELDS, redactSensitiveFields, sanitizeString, sanitizePath, parseDate, sanitizeMetadata, } from './sanitizers.js';
export { ObjectPool, type Poolable, type PoolStats, type PoolConfig, PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule, beadPool, formulaPool, stepPool, convoyPool, moleculePool, type PoolType, getAllPoolStats, getTotalMemorySaved, clearAllPools, preWarmAllPools, getPoolEfficiencySummary, Arena, type ArenaStats, type ArenaConfig, type AllocatableType, type TypeMap, scopedArena, withArena, withArenaSync, ArenaManager, arenaManager, MemoryMonitor, type MemoryStats, type MemoryPressureLevel, type MemoryPressureCallback, type MemoryMonitorConfig, type MemoryMonitorEvents, getMemoryUsage, setMemoryLimit, onMemoryPressure, getDefaultMonitor, disposeDefaultMonitor, MemoryBudgetManager, type MemoryBudget, memoryBudget, Lazy, type LazyState, type LazyOptions, type LazyStats, getLazySingleton, disposeLazySingleton, disposeAllLazySingletons, LazyModule, LazyBridge, LazyWasm, LazyObserver, createLazyProperty, initializeMemorySystem, getSystemMemoryStats, getMemoryReport, triggerMemoryCleanup, shutdownMemorySystem, isMemorySystemInitialized, getMemoryMonitor, type MemorySystemConfig, type MemorySystemState, acquireBead, releaseBead, acquireStep, releaseStep, acquireFormula, releaseFormula, acquireConvoy, releaseConvoy, acquireMolecule, releaseMolecule, } from './memory/index.js';
export default GasTownBridgePlugin;
//# sourceMappingURL=index.d.ts.map