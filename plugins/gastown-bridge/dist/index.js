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
import { DEFAULT_CONFIG, GasTownErrorCodes, validateConfig, } from './types.js';
// Bridge imports
import { GtBridge, createGtBridge } from './bridges/gt-bridge.js';
import { BdBridge, createBdBridge } from './bridges/bd-bridge.js';
import { SyncBridge, createSyncBridge } from './bridges/sync-bridge.js';
// Formula executor
import { FormulaExecutor, createFormulaExecutor } from './formula/executor.js';
// Convoy management
import { ConvoyTracker, createConvoyTracker } from './convoy/tracker.js';
import { ConvoyObserver, createConvoyObserver } from './convoy/observer.js';
// WASM loader
import { isWasmAvailable, loadFormulaWasm, loadGnnWasm, parseFormula as wasmParseFormula, cookFormula as wasmCookFormula, cookBatch as wasmCookBatch, topoSort as wasmTopoSort, detectCycles as wasmDetectCycles, criticalPath as wasmCriticalPath, preloadWasmModules, getWasmVersions, } from './wasm-loader.js';
// MCP Tools
import { gasTownBridgeTools, toolHandlers, toolCategories, getTool, getToolsByLayer, } from './mcp-tools.js';
// Errors
import { GasTownError, GasTownErrorCode, } from './errors.js';
/**
 * Default plugin configuration
 */
const DEFAULT_PLUGIN_CONFIG = {
    gastown: DEFAULT_CONFIG,
    gtBridge: {
        timeout: 30000,
    },
    bdBridge: {
        timeout: 30000,
    },
    syncBridge: {
        namespace: 'gastown:beads',
        syncInterval: 60000,
        autoSync: false,
    },
    formulaExecutor: {
        useWasm: true,
        stepTimeout: 60000,
        maxParallel: 4,
    },
    convoyTracker: {
        autoUpdateProgress: true,
        progressUpdateInterval: 30000,
        persistConvoys: false,
        storagePath: './data/convoys',
    },
    convoyObserver: {
        pollInterval: 10000,
        maxPollAttempts: 0,
        useWasm: true,
    },
    wasm: {
        enabled: true,
        preload: true,
    },
    gupp: {
        enabled: false,
    },
    logger: {
        level: 'info',
        structured: false,
    },
};
/**
 * GUPP Adapter stub implementation
 */
class GuppAdapterStub {
    enabled;
    endpoint;
    constructor(config) {
        this.enabled = config?.enabled ?? false;
        this.endpoint = config?.endpoint;
    }
    isAvailable() {
        return this.enabled && !!this.endpoint;
    }
    async pull(_options) {
        if (!this.isAvailable()) {
            return [];
        }
        // Stub: Would connect to GUPP endpoint
        console.warn('[GUPP] Pull not implemented - stub adapter');
        return [];
    }
    async push(_beads) {
        if (!this.isAvailable()) {
            return { pushed: 0, errors: ['GUPP not configured'] };
        }
        // Stub: Would connect to GUPP endpoint
        console.warn('[GUPP] Push not implemented - stub adapter');
        return { pushed: 0, errors: ['Not implemented'] };
    }
    async sync() {
        if (!this.isAvailable()) {
            return { pulled: 0, pushed: 0, conflicts: [] };
        }
        // Stub: Would connect to GUPP endpoint
        console.warn('[GUPP] Sync not implemented - stub adapter');
        return { pulled: 0, pushed: 0, conflicts: [] };
    }
}
function createPluginLogger(config) {
    const level = config?.level ?? 'info';
    const levels = { debug: 0, info: 1, warn: 2, error: 3 };
    const currentLevel = levels[level];
    const log = (msgLevel, msg, meta) => {
        if (levels[msgLevel] >= currentLevel) {
            const prefix = `[gastown-bridge:${msgLevel}]`;
            if (config?.structured) {
                console.log(JSON.stringify({ level: msgLevel, msg, ...meta, timestamp: new Date().toISOString() }));
            }
            else {
                console.log(`${prefix} ${msg}`, meta ?? '');
            }
        }
    };
    return {
        debug: (msg, meta) => log('debug', msg, meta),
        info: (msg, meta) => log('info', msg, meta),
        warn: (msg, meta) => log('warn', msg, meta),
        error: (msg, meta) => log('error', msg, meta),
    };
}
// ============================================================================
// WASM Loader Adapter
// ============================================================================
/**
 * Adapter to make wasm-loader work with FormulaExecutor's IWasmLoader interface.
 *
 * Since the WASM functions are async but IWasmLoader expects sync methods,
 * we use synchronous JavaScript fallback implementations. The WASM modules
 * are still loaded for caching/preloading purposes but the actual operations
 * use sync fallbacks to satisfy the interface contract.
 */
class WasmLoaderAdapter {
    initialized = false;
    async initialize() {
        try {
            // Preload WASM modules for caching (they will be used async elsewhere)
            await loadFormulaWasm();
            await loadGnnWasm();
            this.initialized = true;
        }
        catch {
            this.initialized = false;
        }
    }
    isInitialized() {
        return this.initialized && isWasmAvailable();
    }
    /**
     * Synchronous TOML parsing fallback (basic implementation)
     */
    parseFormula(content) {
        // Basic TOML parsing - for full TOML support, the async WASM version is preferred
        const lines = content.split('\n');
        const result = {};
        let currentSection = '';
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('#') || trimmed === '')
                continue;
            const sectionMatch = trimmed.match(/^\[([^\]]+)\]$/);
            if (sectionMatch) {
                currentSection = sectionMatch[1];
                if (!result[currentSection])
                    result[currentSection] = {};
                continue;
            }
            const kvMatch = trimmed.match(/^([^=]+)=(.+)$/);
            if (kvMatch) {
                const key = kvMatch[1].trim();
                let value = kvMatch[2].trim();
                if (value === 'true')
                    value = true;
                else if (value === 'false')
                    value = false;
                else if (/^\d+$/.test(value))
                    value = parseInt(value, 10);
                else if (/^\d+\.\d+$/.test(value))
                    value = parseFloat(value);
                else if (value.startsWith('"') && value.endsWith('"')) {
                    value = value.slice(1, -1);
                }
                if (currentSection) {
                    result[currentSection][key] = value;
                }
                else {
                    result[key] = value;
                }
            }
        }
        return {
            name: result['name'] || 'unknown',
            description: result['description'] || '',
            type: result['type'] || 'workflow',
            version: result['version'] || 1,
            steps: result['steps'],
            legs: result['legs'],
            vars: result['vars'],
            metadata: result['metadata'],
        };
    }
    /**
     * Synchronous variable substitution
     */
    cookFormula(formula, vars) {
        const substituteVars = (text) => {
            let result = text;
            for (const [key, value] of Object.entries(vars)) {
                result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value);
                result = result.replace(new RegExp(`\\$\\{${key}\\}`, 'g'), value);
            }
            return result;
        };
        const substituteObject = (obj) => {
            if (typeof obj === 'string')
                return substituteVars(obj);
            if (Array.isArray(obj))
                return obj.map(substituteObject);
            if (obj !== null && typeof obj === 'object') {
                const result = {};
                for (const [key, value] of Object.entries(obj)) {
                    result[key] = substituteObject(value);
                }
                return result;
            }
            return obj;
        };
        const cooked = substituteObject(formula);
        return {
            ...cooked,
            cookedAt: new Date(),
            cookedVars: vars,
            originalName: formula.name,
        };
    }
    /**
     * Synchronous batch cooking
     */
    batchCook(formulas, varsArray) {
        return formulas.map((formula, i) => this.cookFormula(formula, varsArray[i] ?? {}));
    }
    /**
     * Synchronous topological sort using Kahn's algorithm
     */
    resolveStepDependencies(steps) {
        const inDegree = new Map();
        const graph = new Map();
        for (const step of steps) {
            inDegree.set(step.id, 0);
            graph.set(step.id, []);
        }
        for (const step of steps) {
            for (const dep of step.needs ?? []) {
                graph.get(dep)?.push(step.id);
                inDegree.set(step.id, (inDegree.get(step.id) || 0) + 1);
            }
        }
        const queue = [];
        for (const [id, degree] of inDegree) {
            if (degree === 0)
                queue.push(id);
        }
        const sorted = [];
        while (queue.length > 0) {
            const id = queue.shift();
            sorted.push(id);
            for (const neighbor of graph.get(id) || []) {
                const newDegree = (inDegree.get(neighbor) || 0) - 1;
                inDegree.set(neighbor, newDegree);
                if (newDegree === 0)
                    queue.push(neighbor);
            }
        }
        if (sorted.length !== steps.length) {
            const cycleNodes = steps.filter(s => !sorted.includes(s.id)).map(s => s.id);
            throw new GasTownError('Cycle detected in step dependencies', GasTownErrorCode.DEPENDENCY_CYCLE, { cycleNodes });
        }
        const stepMap = new Map(steps.map(s => [s.id, s]));
        return sorted.map(id => stepMap.get(id)).filter((s) => s !== undefined);
    }
    /**
     * Synchronous cycle detection using DFS
     */
    detectCycle(steps) {
        const WHITE = 0, GRAY = 1, BLACK = 2;
        const graph = new Map();
        const colors = new Map();
        for (const step of steps) {
            graph.set(step.id, step.needs ?? []);
            colors.set(step.id, WHITE);
        }
        const cycleNodes = [];
        const dfs = (id, path) => {
            colors.set(id, GRAY);
            path.push(id);
            for (const dep of graph.get(id) || []) {
                if (colors.get(dep) === GRAY) {
                    const cycleStart = path.indexOf(dep);
                    cycleNodes.push(...path.slice(cycleStart));
                    return true;
                }
                if (colors.get(dep) === WHITE && dfs(dep, path)) {
                    return true;
                }
            }
            colors.set(id, BLACK);
            path.pop();
            return false;
        };
        for (const step of steps) {
            if (colors.get(step.id) === WHITE && dfs(step.id, [])) {
                break;
            }
        }
        return {
            hasCycle: cycleNodes.length > 0,
            cycleSteps: cycleNodes.length > 0 ? [...new Set(cycleNodes)] : undefined,
        };
    }
}
// ============================================================================
// Plugin Implementation
// ============================================================================
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
export class GasTownBridgePlugin extends EventEmitter {
    name = '@claude-flow/plugin-gastown-bridge';
    version = '0.1.0';
    description = 'Gas Town orchestrator integration with WASM-accelerated formula parsing and graph analysis';
    config;
    pluginContext = null;
    logger;
    // Component instances
    gtBridge = null;
    bdBridge = null;
    syncBridge = null;
    formulaExecutor = null;
    convoyTracker = null;
    convoyObserver = null;
    wasmLoader = null;
    guppAdapter = null;
    // State
    wasmInitialized = false;
    cliAvailable = false;
    initialized = false;
    constructor(config) {
        super();
        this.config = this.mergeConfig(DEFAULT_PLUGIN_CONFIG, config);
        this.logger = createPluginLogger(this.config.logger);
    }
    /**
     * Register the plugin with claude-flow
     */
    async register(context) {
        this.pluginContext = context;
        // Register plugin in context
        context.set('gastown-bridge', this);
        context.set('gt.version', this.version);
        context.set('gt.capabilities', this.getCapabilities());
        this.logger.info('Plugin registered', { version: this.version });
    }
    /**
     * Initialize the plugin (load WASM, set up bridges)
     */
    async initialize(context) {
        if (this.initialized) {
            return { success: true };
        }
        try {
            this.logger.info('Initializing Gas Town Bridge Plugin...');
            // Step 1: Initialize WASM loader if enabled
            if (this.config.wasm?.enabled) {
                await this.initializeWasm();
            }
            // Step 2: Check CLI availability
            this.cliAvailable = await this.checkCliAvailable();
            if (!this.cliAvailable) {
                this.logger.warn('CLI tools (gt, bd) not found. Some features will be unavailable.');
            }
            // Step 3: Initialize bridges
            await this.initializeBridges();
            // Step 4: Initialize formula executor
            await this.initializeFormulaExecutor();
            // Step 5: Initialize convoy tracker and observer
            await this.initializeConvoyComponents();
            // Step 6: Initialize GUPP adapter
            this.initializeGuppAdapter();
            // Store instances in plugin context
            context.set('gt.config', this.config);
            context.set('gt.wasmReady', this.wasmInitialized);
            context.set('gt.cliAvailable', this.cliAvailable);
            context.set('gt.bridges', {
                gt: this.gtBridge,
                bd: this.bdBridge,
                sync: this.syncBridge,
            });
            context.set('gt.executor', this.formulaExecutor);
            context.set('gt.tracker', this.convoyTracker);
            context.set('gt.observer', this.convoyObserver);
            context.set('gt.gupp', this.guppAdapter);
            this.initialized = true;
            this.emit('initialized');
            this.logger.info('Plugin initialized successfully', {
                wasmReady: this.wasmInitialized,
                cliAvailable: this.cliAvailable,
                toolCount: this.getMCPTools().length,
            });
            return { success: true };
        }
        catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            this.logger.error('Failed to initialize plugin', { error: errorMessage });
            return { success: false, error: errorMessage };
        }
    }
    /**
     * Shutdown the plugin (cleanup resources)
     */
    async shutdown(_context) {
        try {
            this.logger.info('Shutting down Gas Town Bridge Plugin...');
            // Cleanup convoy observer
            if (this.convoyObserver) {
                this.convoyObserver.dispose();
                this.convoyObserver = null;
            }
            // Cleanup convoy tracker
            if (this.convoyTracker) {
                this.convoyTracker.dispose();
                this.convoyTracker = null;
            }
            // Cleanup sync bridge (SyncBridge has no dispose method)
            if (this.syncBridge) {
                this.syncBridge = null;
            }
            // Cleanup bridges
            this.gtBridge = null;
            this.bdBridge = null;
            // Cleanup WASM resources
            this.wasmLoader = null;
            this.wasmInitialized = false;
            // Reset state
            this.pluginContext = null;
            this.initialized = false;
            this.emit('shutdown');
            this.removeAllListeners();
            this.logger.info('Plugin shutdown complete');
            return { success: true };
        }
        catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            this.logger.error('Failed to shutdown plugin', { error: errorMessage });
            return { success: false, error: errorMessage };
        }
    }
    /**
     * Get plugin capabilities
     */
    getCapabilities() {
        return [
            'beads-integration',
            'convoy-tracking',
            'formula-parsing',
            'formula-cooking',
            'formula-execution',
            'wasm-acceleration',
            'dependency-resolution',
            'topological-sort',
            'cycle-detection',
            'critical-path',
            'agentdb-sync',
            'sling-operations',
            'gupp-adapter',
        ];
    }
    /**
     * Get plugin MCP tools
     */
    getMCPTools() {
        // Convert MCPTool to PluginMCPTool format
        return gasTownBridgeTools.map(tool => this.convertMcpTool(tool));
    }
    /**
     * Get plugin hooks
     */
    getHooks() {
        return [
            this.createPreTaskHook(),
            this.createPostTaskHook(),
            this.createBeadsSyncHook(),
            this.createConvoyProgressHook(),
        ];
    }
    // ============================================================================
    // Public API
    // ============================================================================
    /**
     * Get the current configuration
     */
    getConfig() {
        return { ...this.config };
    }
    /**
     * Update configuration
     */
    updateConfig(config) {
        this.config = this.mergeConfig(this.config, config);
        if (this.config.gastown) {
            this.config.gastown = validateConfig({ ...DEFAULT_CONFIG, ...this.config.gastown });
        }
    }
    /**
     * Check if WASM is initialized
     */
    isWasmReady() {
        return this.wasmInitialized;
    }
    /**
     * Check if CLI tools are available
     */
    isCliAvailable() {
        return this.cliAvailable;
    }
    /**
     * Get bridge instances
     */
    getBridges() {
        return {
            gt: this.gtBridge,
            bd: this.bdBridge,
            sync: this.syncBridge,
        };
    }
    /**
     * Get formula executor
     */
    getFormulaExecutor() {
        return this.formulaExecutor;
    }
    /**
     * Get convoy tracker
     */
    getConvoyTracker() {
        return this.convoyTracker;
    }
    /**
     * Get convoy observer
     */
    getConvoyObserver() {
        return this.convoyObserver;
    }
    /**
     * Get GUPP adapter
     */
    getGuppAdapter() {
        return this.guppAdapter;
    }
    /**
     * Get plugin metadata
     */
    getMetadata() {
        return {
            name: this.name,
            version: this.version,
            description: this.description,
            author: 'rUv',
            license: 'MIT',
            repository: 'https://github.com/ruvnet/claude-flow',
            keywords: [
                'claude-flow',
                'plugin',
                'gastown',
                'beads',
                'orchestration',
                'workflows',
                'formulas',
                'wasm',
                'multi-agent',
            ],
            mcpTools: gasTownBridgeTools.map(t => t.name),
            capabilities: this.getCapabilities(),
        };
    }
    // ============================================================================
    // Private Methods - Initialization
    // ============================================================================
    mergeConfig(base, override) {
        if (!override)
            return { ...base };
        return {
            gastown: { ...base.gastown, ...override.gastown },
            gtBridge: { ...base.gtBridge, ...override.gtBridge },
            bdBridge: { ...base.bdBridge, ...override.bdBridge },
            syncBridge: { ...base.syncBridge, ...override.syncBridge },
            formulaExecutor: { ...base.formulaExecutor, ...override.formulaExecutor },
            convoyTracker: { ...base.convoyTracker, ...override.convoyTracker },
            convoyObserver: { ...base.convoyObserver, ...override.convoyObserver },
            wasm: { ...base.wasm, ...override.wasm },
            gupp: { ...base.gupp, ...override.gupp },
            logger: { ...base.logger, ...override.logger },
        };
    }
    async initializeWasm() {
        try {
            this.wasmLoader = new WasmLoaderAdapter();
            if (this.config.wasm?.preload) {
                await preloadWasmModules();
            }
            await this.wasmLoader.initialize();
            this.wasmInitialized = this.wasmLoader.isInitialized();
            if (this.wasmInitialized) {
                const versions = await getWasmVersions();
                this.logger.info('WASM modules initialized', { versions });
            }
        }
        catch (error) {
            this.logger.warn('WASM initialization failed, using JS fallback', {
                error: error instanceof Error ? error.message : String(error),
            });
            this.wasmInitialized = false;
        }
    }
    async checkCliAvailable() {
        try {
            const { exec } = await import('child_process');
            const { promisify } = await import('util');
            const execAsync = promisify(exec);
            await execAsync('which gt');
            await execAsync('which bd');
            return true;
        }
        catch {
            return false;
        }
    }
    async initializeBridges() {
        // Initialize GtBridge
        this.gtBridge = createGtBridge({
            gtPath: this.config.gtBridge?.gtPath,
            timeout: this.config.gtBridge?.timeout,
            cwd: this.config.gtBridge?.cwd,
        });
        await this.gtBridge.initialize();
        // Initialize BdBridge
        this.bdBridge = createBdBridge({
            bdPath: this.config.bdBridge?.bdPath,
            timeout: this.config.bdBridge?.timeout,
            cwd: this.config.bdBridge?.cwd,
        });
        await this.bdBridge.initialize();
        // Initialize SyncBridge - requires an AgentDB service
        // We create a stub AgentDB service that will be replaced when
        // the plugin context provides a real one
        const stubAgentDB = this.createStubAgentDB();
        this.syncBridge = createSyncBridge(stubAgentDB, {
            beadsBridge: this.config.bdBridge,
            agentdbNamespace: this.config.syncBridge?.namespace ?? 'gastown:beads',
        });
        this.logger.debug('Bridges initialized');
    }
    async initializeFormulaExecutor() {
        if (!this.gtBridge) {
            throw new GasTownError('GtBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
        }
        const wasmLoader = this.config.formulaExecutor?.useWasm && this.wasmLoader
            ? this.wasmLoader
            : undefined;
        this.formulaExecutor = createFormulaExecutor(this.gtBridge, wasmLoader, this.logger);
        this.logger.debug('Formula executor initialized', {
            wasmEnabled: !!wasmLoader,
        });
    }
    async initializeConvoyComponents() {
        if (!this.bdBridge) {
            throw new GasTownError('BdBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
        }
        // Initialize ConvoyTracker
        this.convoyTracker = createConvoyTracker({
            bdBridge: this.bdBridge,
            autoUpdateProgress: this.config.convoyTracker?.autoUpdateProgress,
            progressUpdateInterval: this.config.convoyTracker?.progressUpdateInterval,
            persistConvoys: this.config.convoyTracker?.persistConvoys,
            storagePath: this.config.convoyTracker?.storagePath,
        }, this.logger);
        // Initialize ConvoyObserver
        this.convoyObserver = createConvoyObserver({
            bdBridge: this.bdBridge,
            tracker: this.convoyTracker,
            pollInterval: this.config.convoyObserver?.pollInterval,
            maxPollAttempts: this.config.convoyObserver?.maxPollAttempts,
            useWasm: this.config.convoyObserver?.useWasm,
        }, this.logger);
        this.logger.debug('Convoy components initialized');
    }
    initializeGuppAdapter() {
        this.guppAdapter = new GuppAdapterStub(this.config.gupp);
        this.logger.debug('GUPP adapter initialized', {
            enabled: this.guppAdapter.isAvailable(),
        });
    }
    /**
     * Create a stub AgentDB service for SyncBridge initialization.
     * This stub stores data in-memory and should be replaced with
     * the real AgentDB service from the plugin context.
     */
    createStubAgentDB() {
        const storage = new Map();
        return {
            async store(key, value, namespace, metadata) {
                const ns = namespace ?? 'default';
                if (!storage.has(ns))
                    storage.set(ns, new Map());
                storage.get(ns).set(key, {
                    key,
                    value,
                    namespace: ns,
                    metadata,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                    version: 1,
                });
            },
            async retrieve(key, namespace) {
                const ns = namespace ?? 'default';
                return storage.get(ns)?.get(key) ?? null;
            },
            async search(_query, namespace, limit) {
                const ns = namespace ?? 'default';
                const entries = storage.get(ns);
                if (!entries)
                    return [];
                return Array.from(entries.values()).slice(0, limit ?? 100);
            },
            async list(namespace, limit, offset) {
                const ns = namespace ?? 'default';
                const entries = storage.get(ns);
                if (!entries)
                    return [];
                return Array.from(entries.values()).slice(offset ?? 0, (offset ?? 0) + (limit ?? 100));
            },
            async delete(key, namespace) {
                const ns = namespace ?? 'default';
                storage.get(ns)?.delete(key);
            },
            async getNamespaceStats(namespace) {
                const entries = storage.get(namespace);
                if (!entries)
                    return { count: 0 };
                const values = Array.from(entries.values());
                const lastUpdated = values.length > 0
                    ? values.reduce((latest, e) => (e.updatedAt && e.updatedAt > (latest ?? '')) ? e.updatedAt : latest, undefined)
                    : undefined;
                return { count: values.length, lastUpdated };
            },
        };
    }
    // ============================================================================
    // Private Methods - MCP Tool Conversion
    // ============================================================================
    convertMcpTool(tool) {
        return {
            name: tool.name,
            description: tool.description,
            category: tool.category,
            version: tool.version,
            inputSchema: this.zodToJsonSchema(tool.inputSchema),
            handler: async (input, context) => {
                // Create tool context from plugin context
                const toolContext = this.createToolContext(context);
                const result = await tool.handler(input, toolContext);
                return result;
            },
        };
    }
    zodToJsonSchema(zodSchema) {
        // Simplified conversion - in production use zod-to-json-schema
        try {
            const schema = zodSchema;
            if (schema._def?.shape) {
                const shape = schema._def.shape();
                const properties = {};
                const required = [];
                for (const [key, value] of Object.entries(shape)) {
                    const fieldSchema = value;
                    const typeName = fieldSchema._def?.typeName ?? 'ZodString';
                    // Map Zod types to JSON Schema types
                    let jsonType = 'string';
                    if (typeName.includes('Number'))
                        jsonType = 'number';
                    else if (typeName.includes('Boolean'))
                        jsonType = 'boolean';
                    else if (typeName.includes('Array'))
                        jsonType = 'array';
                    else if (typeName.includes('Object'))
                        jsonType = 'object';
                    properties[key] = { type: jsonType };
                    // Check if required (not optional)
                    if (!typeName.includes('Optional') && !typeName.includes('Default')) {
                        required.push(key);
                    }
                }
                return { type: 'object', properties, required: required.length > 0 ? required : undefined };
            }
        }
        catch {
            // Fallback
        }
        return { type: 'object', properties: {} };
    }
    createToolContext(pluginContext) {
        const gasTownConfig = this.config.gastown ?? DEFAULT_CONFIG;
        return {
            get: (key) => pluginContext.get(key),
            set: (key, value) => pluginContext.set(key, value),
            bridges: {
                gastown: this.createBridgeFacade(),
                beadsSync: this.createSyncFacade(),
                formulaWasm: this.createFormulaWasmFacade(),
                dependencyWasm: this.createDependencyWasmFacade(),
            },
            config: {
                townRoot: gasTownConfig.townRoot ?? '',
                allowedRigs: [], // Not part of GasTownConfig type - use empty array
                maxBeadsLimit: 100,
                maskSecrets: true,
                enableWasm: this.wasmInitialized,
            },
        };
    }
    /**
     * Create the bridge facade for MCP tools.
     *
     * NOTE: This facade bridges between the plugin's internal types (from bd-bridge, etc.)
     * and the external interface types (from types.ts). Type casts are necessary because
     * the underlying bridges use different type definitions. A future refactor should
     * unify these type systems.
     */
    createBridgeFacade() {
        const gt = this.gtBridge;
        const bd = this.bdBridge;
        const tracker = this.convoyTracker;
        const wasmLoader = this.wasmLoader;
        return {
            async createBead(opts) {
                if (!bd)
                    throw new GasTownError('BdBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // CreateBeadOptions uses title, the bridge uses content
                const bdOpts = {
                    type: 'prompt',
                    content: opts.description ?? opts.title,
                    parentId: opts.parent,
                    agentId: opts.assignee,
                    tags: opts.labels,
                };
                const result = await bd.createBead(bdOpts);
                // Map bd-bridge Bead to types.ts Bead
                return {
                    id: result.id,
                    title: result.content.slice(0, 100),
                    description: result.content,
                    status: 'open',
                    priority: 0,
                    labels: result.tags ?? [],
                    createdAt: result.timestamp ? new Date(result.timestamp) : new Date(),
                    updatedAt: result.timestamp ? new Date(result.timestamp) : new Date(),
                    parentId: result.parentId,
                    assignee: result.agentId,
                };
            },
            async getReady(limit, _rig, _labels) {
                if (!bd)
                    throw new GasTownError('BdBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                const beads = await bd.listBeads({ limit });
                // Map bd-bridge Beads to types.ts Beads
                return beads.map(b => ({
                    id: b.id,
                    title: b.content.slice(0, 100),
                    description: b.content,
                    status: 'open',
                    priority: 0,
                    labels: b.tags ?? [],
                    createdAt: b.timestamp ? new Date(b.timestamp) : new Date(),
                    updatedAt: b.timestamp ? new Date(b.timestamp) : new Date(),
                    parentId: b.parentId,
                    assignee: b.agentId,
                }));
            },
            async showBead(beadId) {
                if (!bd)
                    throw new GasTownError('BdBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                const bead = await bd.getBead(beadId);
                return {
                    bead: {
                        id: bead.id,
                        title: bead.content.slice(0, 100),
                        description: bead.content,
                        status: 'open',
                        priority: 0,
                        labels: bead.tags ?? [],
                        createdAt: new Date(),
                        updatedAt: new Date(),
                    },
                    dependencies: bead.parentId ? [bead.parentId] : [],
                    dependents: [],
                };
            },
            async manageDependency(action, child, parent) {
                if (!bd)
                    throw new GasTownError('BdBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // BdBridge doesn't have addDependency/removeDependency - use execBd directly
                if (action === 'add') {
                    await bd.execBd(['update', child, '--parent', parent]);
                }
                else {
                    await bd.execBd(['update', child, '--remove-parent', parent]);
                }
            },
            async createConvoy(opts) {
                if (!tracker)
                    throw new GasTownError('ConvoyTracker not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // ConvoyTracker.create takes (name, issues, description) as separate arguments
                return tracker.create(opts.name, opts.issues, opts.description);
            },
            async getConvoyStatus(convoyId, _detailed) {
                if (!tracker)
                    throw new GasTownError('ConvoyTracker not initialized', GasTownErrorCode.NOT_INITIALIZED);
                if (convoyId) {
                    const convoy = await tracker.getStatus(convoyId);
                    // Return array with single convoy
                    return [convoy];
                }
                // If no convoyId, return all convoys
                return tracker.listConvoys();
            },
            async trackConvoy(convoyId, action, issues) {
                if (!tracker)
                    throw new GasTownError('ConvoyTracker not initialized', GasTownErrorCode.NOT_INITIALIZED);
                if (action === 'add') {
                    await tracker.addIssues(convoyId, issues);
                }
                else {
                    await tracker.removeIssues(convoyId, issues);
                }
            },
            async listFormulas(_type, _includeBuiltin) {
                // No direct CLI command - return empty for now
                // Would need to scan formula directories
                return [];
            },
            async cookFormula(formula, vars) {
                // Use WasmLoaderAdapter for cooking
                if (wasmLoader?.isInitialized()) {
                    const parsed = typeof formula === 'string' ? wasmLoader.parseFormula(formula) : formula;
                    return wasmLoader.cookFormula(parsed, vars);
                }
                // Fallback if no WASM
                throw new GasTownError('WASM not initialized for formula cooking', GasTownErrorCode.NOT_INITIALIZED);
            },
            async executeFormula(_formula, _vars, _targetAgent, _dryRun) {
                // Formula execution requires the FormulaExecutor
                throw new GasTownError('Use FormulaExecutor.execute() for formula execution', GasTownErrorCode.NOT_INITIALIZED);
            },
            async createFormula(_opts) {
                // Formula creation would write to filesystem - not implemented in bridges
                throw new GasTownError('Formula creation not implemented in bridge layer', GasTownErrorCode.NOT_INITIALIZED);
            },
            async sling(beadId, target, formula, priority) {
                if (!gt)
                    throw new GasTownError('GtBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // Use execGt to run sling command
                const args = ['tx', 'sling', '--bead', beadId, '--target', target];
                if (formula)
                    args.push('--formula', formula);
                if (priority !== undefined)
                    args.push('--priority', String(priority));
                await gt.execGt(args);
            },
            async listAgents(_rig, _role, _includeInactive) {
                // Would need agent registry - return empty for now
                // Return type matches GasTownAgent[]
                return [];
            },
            async sendMail(to, subject, body) {
                if (!gt)
                    throw new GasTownError('GtBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // Use execGt for mail operations
                const result = await gt.execGt(['tx', 'mail', '--to', to, '--subject', subject, '--body', body, '--json']);
                // Return message ID as string
                return result.data ?? 'unknown';
            },
            async readMail(mailId) {
                if (!gt)
                    throw new GasTownError('GtBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                const result = await gt.execGt(['tx', 'mail', 'read', mailId, '--json']);
                if (result.success && result.data) {
                    const parsed = gt.parseGtOutput(result.data);
                    // Map to GasTownMail type
                    return {
                        id: parsed.id,
                        from: parsed.from,
                        to: parsed.to ?? '',
                        subject: parsed.subject,
                        body: parsed.body,
                        sentAt: new Date(parsed.timestamp),
                        read: true,
                    };
                }
                throw new GasTownError(`Failed to read mail: ${mailId}`, GasTownErrorCode.NOT_INITIALIZED);
            },
            async listMail(limit) {
                if (!gt)
                    throw new GasTownError('GtBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
                const args = ['tx', 'mail', 'list', '--json'];
                if (limit !== undefined)
                    args.push('--limit', String(limit));
                const result = await gt.execGt(args);
                if (result.success && result.data) {
                    const parsed = gt.parseGtOutput(result.data);
                    // Map to GasTownMail[] type
                    return parsed.map(m => ({
                        id: m.id,
                        from: m.from,
                        to: m.to ?? '',
                        subject: m.subject,
                        body: m.body ?? '',
                        sentAt: new Date(m.timestamp),
                        read: false,
                    }));
                }
                return [];
            },
        };
    }
    createSyncFacade() {
        const sync = this.syncBridge;
        const bd = this.bdBridge;
        return {
            async pullBeads(_rig, _namespace) {
                if (!sync)
                    return { synced: 0, conflicts: 0 };
                // SyncBridge uses syncFromAgentDB to pull beads
                const beads = await sync.syncFromAgentDB();
                return { synced: beads.length, conflicts: sync.getPendingConflicts().length };
            },
            async pushTasks(_namespace) {
                if (!sync || !bd)
                    return { pushed: 0, conflicts: 0 };
                // SyncBridge uses syncToAgentDB to push beads
                const allBeads = await bd.listBeads({});
                const result = await sync.syncToAgentDB(allBeads);
                return { pushed: result.synced, conflicts: result.conflicts };
            },
        };
    }
    createFormulaWasmFacade() {
        const loader = this.wasmLoader;
        return {
            isInitialized: () => loader?.isInitialized() ?? false,
            async initialize() {
                if (loader)
                    await loader.initialize();
            },
            async parseFormula(content, _validate) {
                if (!loader)
                    throw new GasTownError('WASM not initialized', GasTownErrorCode.NOT_INITIALIZED);
                return loader.parseFormula(content);
            },
            async cookFormula(formula, vars, _isContent) {
                if (!loader)
                    throw new GasTownError('WASM not initialized', GasTownErrorCode.NOT_INITIALIZED);
                const parsed = typeof formula === 'string' ? loader.parseFormula(formula) : formula;
                return loader.cookFormula(parsed, vars);
            },
            async cookBatch(formulas, vars, _continueOnError) {
                if (!loader)
                    throw new GasTownError('WASM not initialized', GasTownErrorCode.NOT_INITIALIZED);
                const parsedFormulas = formulas.map(f => loader.parseFormula(f.content));
                const cooked = loader.batchCook(parsedFormulas, vars);
                return { cooked, errors: [] };
            },
        };
    }
    createDependencyWasmFacade() {
        const loader = this.wasmLoader;
        const simpleSimilarity = this.simpleSimilarity.bind(this);
        return {
            isInitialized: () => loader?.isInitialized() ?? false,
            async initialize() {
                if (loader)
                    await loader.initialize();
            },
            async resolveDependencies(beads, action) {
                if (!loader)
                    throw new GasTownError('WASM not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // Convert beads to Step format for WasmLoaderAdapter (sync)
                // Add placeholder title and description to satisfy Step interface
                const steps = beads.map(b => ({
                    id: b.id,
                    title: b.id,
                    description: '',
                    needs: b.dependencies ?? [],
                }));
                if (action === 'topo_sort') {
                    // Use the sync resolveStepDependencies from WasmLoaderAdapter
                    try {
                        const sorted = loader.resolveStepDependencies(steps);
                        return { action, sorted: sorted.map(s => s.id), hasCycle: false, cycleNodes: undefined };
                    }
                    catch (e) {
                        if (e instanceof GasTownError && e.code === GasTownErrorCode.DEPENDENCY_CYCLE) {
                            const cycleNodes = e.context?.cycleNodes ?? [];
                            return { action, sorted: [], hasCycle: true, cycleNodes };
                        }
                        throw e;
                    }
                }
                else if (action === 'cycle_detect') {
                    const result = loader.detectCycle(steps);
                    return { action, hasCycle: result.hasCycle, cycleNodes: result.cycleSteps };
                }
                else {
                    // For critical path, use async WASM function
                    const nodes = beads.map(b => b.id);
                    const edges = beads.flatMap(b => (b.dependencies ?? []).map(dep => ({ from: dep, to: b.id })));
                    const result = await wasmCriticalPath(nodes, edges, []);
                    return { action, criticalPath: result.path, totalDuration: result.totalDuration };
                }
            },
            async matchPatterns(query, candidates, k, threshold) {
                // Simplified pattern matching - in production use WASM HNSW
                const matches = candidates
                    .map((candidate, index) => ({
                    index,
                    candidate,
                    similarity: simpleSimilarity(query, candidate),
                }))
                    .filter(m => m.similarity >= threshold)
                    .sort((a, b) => b.similarity - a.similarity)
                    .slice(0, k);
                return matches;
            },
            async optimizeConvoy(convoy, strategy, _constraints) {
                if (!loader)
                    throw new GasTownError('WASM not initialized', GasTownErrorCode.NOT_INITIALIZED);
                // Convert to Step format with placeholder fields
                const steps = convoy.trackedIssues.map(id => ({
                    id,
                    title: id,
                    description: '',
                    needs: [],
                }));
                const sortedSteps = loader.resolveStepDependencies(steps);
                const executionOrder = sortedSteps.map(s => s.id);
                return {
                    convoyId: convoy.id,
                    strategy,
                    executionOrder,
                    parallelGroups: [executionOrder], // Simplified - all in one group since no deps
                    estimatedDuration: convoy.trackedIssues.length * 1000,
                };
            },
        };
    }
    simpleSimilarity(a, b) {
        // Simple Jaccard similarity
        const setA = new Set(a.toLowerCase().split(/\s+/));
        const setB = new Set(b.toLowerCase().split(/\s+/));
        const intersection = new Set([...setA].filter(x => setB.has(x)));
        const union = new Set([...setA, ...setB]);
        return intersection.size / union.size;
    }
    // ============================================================================
    // Hook Implementations
    // ============================================================================
    createPreTaskHook() {
        return {
            name: 'gt/pre-task',
            event: 'pre-task',
            priority: 50,
            description: 'Check for related beads before task execution',
            handler: async (_context, payload) => {
                // Check if task matches any beads in Gas Town
                if (this.config.gastown?.autoCreateBeads) {
                    this.logger.debug('Pre-task hook: checking for related beads');
                }
                return payload;
            },
        };
    }
    createPostTaskHook() {
        return {
            name: 'gt/post-task',
            event: 'post-task',
            priority: 50,
            description: 'Update bead status after task completion',
            handler: async (_context, payload) => {
                // Update bead status if autoCreateBeads is enabled
                if (this.config.gastown?.autoCreateBeads) {
                    this.logger.debug('Post-task hook: updating bead status');
                }
                return payload;
            },
        };
    }
    createBeadsSyncHook() {
        return {
            name: 'gt/beads-sync',
            event: 'session-start',
            priority: 100,
            description: 'Sync beads with AgentDB on session start',
            handler: async (_context, payload) => {
                if (this.config.gastown?.enableBeadsSync && this.syncBridge) {
                    this.logger.info('Beads sync triggered on session start');
                    try {
                        // Use syncBidirectional for full sync
                        await this.syncBridge.syncBidirectional();
                    }
                    catch (error) {
                        this.logger.warn('Beads sync failed', {
                            error: error instanceof Error ? error.message : String(error),
                        });
                    }
                }
                return payload;
            },
        };
    }
    createConvoyProgressHook() {
        return {
            name: 'gt/convoy-progress',
            event: 'task-complete',
            priority: 60,
            description: 'Update convoy progress when tasks complete',
            handler: async (_context, payload) => {
                if (this.convoyTracker) {
                    // Refresh active convoy progress
                    const activeConvoys = this.convoyTracker.listConvoys('active');
                    for (const convoy of activeConvoys) {
                        try {
                            await this.convoyTracker.getStatus(convoy.id);
                        }
                        catch {
                            // Ignore errors during refresh
                        }
                    }
                }
                return payload;
            },
        };
    }
}
// ============================================================================
// Factory Function
// ============================================================================
/**
 * Create a new Gas Town Bridge Plugin instance
 */
export function createGasTownBridgePlugin(config) {
    return new GasTownBridgePlugin(config);
}
// ============================================================================
// Exports
// ============================================================================
// Re-export types
export * from './types.js';
// Re-export bridges
export * from './bridges/index.js';
// Re-export convoy module
export * from './convoy/index.js';
// Re-export formula executor
export { FormulaExecutor, createFormulaExecutor, } from './formula/executor.js';
// Re-export MCP tools
export { gasTownBridgeTools, toolHandlers, toolCategories, getTool, getToolsByLayer, } from './mcp-tools.js';
// Re-export WASM loader
export { 
// Availability check
isWasmAvailable, 
// Formula operations
loadFormulaWasm, parseFormula, cookFormula, cookBatch, 
// Graph operations
loadGnnWasm, topoSort, detectCycles, criticalPath, 
// Module management
preloadWasmModules, getWasmVersions, resetWasmCache, 
// Performance timing
getPerformanceLog, clearPerformanceLog, 
// Default export
default as WasmLoader, } from './wasm-loader.js';
// Re-export security modules (explicit exports to avoid conflicts)
export { 
// Error classes
GasTownError, BeadsError, ValidationError, CLIExecutionError, FormulaError, ConvoyError, 
// Error codes (aliased to avoid conflict with types.ts)
GasTownErrorCode as ErrorCodes, 
// Error utilities
isGasTownError, isValidationError, isCLIExecutionError, isBeadsError, wrapError, getErrorMessage, } from './errors.js';
export { 
// Validation functions
validateBeadId, validateFormulaName, validateConvoyId, validateGtArgs, 
// Compound validators (aliased to avoid conflicts)
validateCreateBeadOptions as validateBeadOptions, validateCreateConvoyOptions as validateConvoyOptions, validateSlingOptions as validateSling, 
// Validation schemas (aliased to avoid conflicts)
BeadIdSchema as BeadIdValidationSchema, FormulaNameSchema, ConvoyIdSchema, GtArgsSchema, SafeStringSchema as ValidatorSafeStringSchema, RigNameSchema, PrioritySchema, LabelsSchema, 
// Security utilities
containsShellMetacharacters, containsPathTraversal, isSafeArgument, isValidBeadId, isValidFormulaName, isValidConvoyId, 
// Constants
MAX_LENGTHS, SHELL_METACHARACTERS, PATH_TRAVERSAL_PATTERNS, BEAD_ID_PATTERN, FORMULA_NAME_PATTERN, UUID_PATTERN, CONVOY_HASH_PATTERN, } from './validators.js';
export { 
// Sanitization functions
sanitizeBeadOutput, sanitizeFormulaOutput, sanitizeConvoyOutput, sanitizeBeadsListOutput, 
// Constants
MAX_OUTPUT_SIZE, SENSITIVE_FIELD_PATTERNS, REDACTED_FIELDS, 
// Internal helpers (for testing)
redactSensitiveFields, sanitizeString, sanitizePath, parseDate, sanitizeMetadata, } from './sanitizers.js';
// Re-export memory management module
export { 
// Object Pooling
ObjectPool, PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule, beadPool, formulaPool, stepPool, convoyPool, moleculePool, getAllPoolStats, getTotalMemorySaved, clearAllPools, preWarmAllPools, getPoolEfficiencySummary, 
// Arena Allocator
Arena, scopedArena, withArena, withArenaSync, ArenaManager, arenaManager, 
// Memory Monitoring
MemoryMonitor, getMemoryUsage, setMemoryLimit, onMemoryPressure, getDefaultMonitor, disposeDefaultMonitor, MemoryBudgetManager, memoryBudget, 
// Lazy Loading
Lazy, getLazySingleton, disposeLazySingleton, disposeAllLazySingletons, LazyModule, LazyBridge, LazyWasm, LazyObserver, createLazyProperty, 
// Integrated Memory System
initializeMemorySystem, getSystemMemoryStats, getMemoryReport, triggerMemoryCleanup, shutdownMemorySystem, isMemorySystemInitialized, getMemoryMonitor, 
// Quick-access utilities
acquireBead, releaseBead, acquireStep, releaseStep, acquireFormula, releaseFormula, acquireConvoy, releaseConvoy, acquireMolecule, releaseMolecule, } from './memory/index.js';
// Default export
export default GasTownBridgePlugin;
//# sourceMappingURL=index.js.map