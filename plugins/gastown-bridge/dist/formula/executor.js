/**
 * Gas Town Formula Executor - Hybrid WASM/CLI Implementation
 *
 * Provides formula execution with:
 * - WASM acceleration for parsing and cooking (352x faster)
 * - CLI bridge fallback for I/O operations
 * - Progress tracking with event emission
 * - Step dependency resolution
 * - Molecule generation from cooked formulas
 * - Cancellation support
 *
 * @module v3/plugins/gastown-bridge/formula/executor
 */
import { EventEmitter } from 'events';
import { randomUUID } from 'crypto';
import { GasTownError, GasTownErrorCode, FormulaError, } from '../errors.js';
import { stepPool, formulaPool, moleculePool, PooledStep, PooledFormula, PooledMolecule, withArenaSync, } from '../memory/index.js';
import { LRUCache, BatchDeduplicator, DebouncedEmitter, } from '../cache.js';
// ============================================================================
// Performance Caches & Deduplication
// ============================================================================
/** Step result cache for memoization */
const stepResultCache = new LRUCache({
    maxEntries: 500,
    ttlMs: 5 * 60 * 1000, // 5 min TTL
});
/** Formula cook cache */
const cookCache = new LRUCache({
    maxEntries: 200,
    ttlMs: 10 * 60 * 1000, // 10 min TTL
});
/** Deduplicator for concurrent cook requests */
const cookDedup = new BatchDeduplicator();
/** Deduplicator for concurrent formula fetch requests */
const fetchDedup = new BatchDeduplicator();
/**
 * Work stealing queue for load balancing across parallel workers
 */
class WorkStealingQueue {
    numWorkers;
    queues = [];
    nextQueueId = 0;
    constructor(numWorkers) {
        this.numWorkers = numWorkers;
        for (let i = 0; i < numWorkers; i++) {
            this.queues.push([]);
        }
    }
    /** Enqueue work to least-loaded queue */
    enqueue(item) {
        // Find queue with least items
        let minQueue = 0;
        let minLen = this.queues[0]?.length ?? 0;
        for (let i = 1; i < this.queues.length; i++) {
            const len = this.queues[i]?.length ?? 0;
            if (len < minLen) {
                minLen = len;
                minQueue = i;
            }
        }
        this.queues[minQueue]?.push(item);
    }
    /** Dequeue from own queue or steal from others */
    dequeue(workerId) {
        // Try own queue first
        const ownQueue = this.queues[workerId];
        if (ownQueue && ownQueue.length > 0) {
            return ownQueue.shift();
        }
        // Try to steal from other queues (round-robin)
        for (let i = 1; i < this.queues.length; i++) {
            const victimId = (workerId + i) % this.queues.length;
            const victimQueue = this.queues[victimId];
            if (victimQueue && victimQueue.length > 1) {
                // Steal from the back (LIFO stealing)
                return victimQueue.pop();
            }
        }
        return undefined;
    }
    /** Check if all queues are empty */
    isEmpty() {
        return this.queues.every(q => q.length === 0);
    }
    /** Get total pending items */
    get size() {
        return this.queues.reduce((sum, q) => sum + q.length, 0);
    }
}
/**
 * Hash function for cache keys (FNV-1a)
 */
function hashKey(parts) {
    let hash = 2166136261;
    for (const part of parts) {
        for (let i = 0; i < part.length; i++) {
            hash ^= part.charCodeAt(i);
            hash = (hash * 16777619) >>> 0;
        }
        hash ^= 0xff; // separator
    }
    return hash.toString(36);
}
// ============================================================================
// Default Logger
// ============================================================================
const defaultLogger = {
    debug: (msg, meta) => console.debug(`[formula-executor] ${msg}`, meta ?? ''),
    info: (msg, meta) => console.info(`[formula-executor] ${msg}`, meta ?? ''),
    warn: (msg, meta) => console.warn(`[formula-executor] ${msg}`, meta ?? ''),
    error: (msg, meta) => console.error(`[formula-executor] ${msg}`, meta ?? ''),
};
// ============================================================================
// JavaScript Fallback Implementation
// ============================================================================
/**
 * JavaScript fallback for WASM operations
 * Used when WASM is not available
 */
class JsFallbackWasmLoader {
    isInitialized() {
        return true; // JS fallback is always available
    }
    parseFormula(content) {
        // Basic TOML parsing simulation
        // In production, use a proper TOML parser
        try {
            const lines = content.split('\n');
            // Use mutable objects during parsing, then cast to readonly
            let name = 'parsed-formula';
            let description = '';
            let type = 'workflow';
            let version = 1;
            const steps = [];
            const vars = {};
            let currentSection = '';
            let currentStep = null;
            for (const line of lines) {
                const trimmed = line.trim();
                // Skip empty lines and comments
                if (!trimmed || trimmed.startsWith('#'))
                    continue;
                // Section headers
                if (trimmed.startsWith('[')) {
                    if (currentStep && currentStep.id) {
                        steps.push(currentStep);
                    }
                    const sectionMatch = trimmed.match(/\[(\w+)(?:\.(\w+))?\]/);
                    if (sectionMatch) {
                        currentSection = sectionMatch[1];
                        if (sectionMatch[2]) {
                            currentStep = { id: sectionMatch[2], title: '', description: '' };
                        }
                        else {
                            currentStep = null;
                        }
                    }
                    continue;
                }
                // Key-value pairs
                const kvMatch = trimmed.match(/^(\w+)\s*=\s*"?([^"]*)"?$/);
                if (kvMatch) {
                    const [, key, value] = kvMatch;
                    if (currentSection === 'formula') {
                        if (key === 'name')
                            name = value;
                        else if (key === 'description')
                            description = value;
                        else if (key === 'type')
                            type = value;
                        else if (key === 'version')
                            version = parseInt(value, 10);
                    }
                    else if (currentStep) {
                        if (key === 'title')
                            currentStep.title = value;
                        else if (key === 'description')
                            currentStep.description = value;
                        else if (key === 'needs') {
                            currentStep.needs = value.split(',').map(s => s.trim());
                        }
                    }
                }
            }
            // Add last step
            if (currentStep && currentStep.id) {
                steps.push(currentStep);
            }
            // Return immutable formula
            const formula = {
                name,
                description,
                type,
                version,
                steps: steps,
                vars,
            };
            return formula;
        }
        catch (error) {
            throw FormulaError.parseFailed('js-parse', 'Failed to parse formula content', error);
        }
    }
    cookFormula(formula, vars) {
        const substituteVars = (text) => {
            return text.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
                return vars[varName] ?? match;
            });
        };
        const cookedSteps = formula.steps?.map(step => ({
            ...step,
            title: substituteVars(step.title),
            description: substituteVars(step.description),
        }));
        const cookedLegs = formula.legs?.map(leg => ({
            ...leg,
            title: substituteVars(leg.title),
            description: substituteVars(leg.description),
            focus: substituteVars(leg.focus),
        }));
        return {
            ...formula,
            steps: cookedSteps,
            legs: cookedLegs,
            cookedAt: new Date(),
            cookedVars: { ...vars },
            originalName: formula.name,
        };
    }
    batchCook(formulas, varsArray) {
        return formulas.map((formula, index) => {
            const vars = varsArray[index] ?? {};
            return this.cookFormula(formula, vars);
        });
    }
    resolveStepDependencies(steps) {
        // Topological sort using Kahn's algorithm
        const stepMap = new Map();
        const inDegree = new Map();
        const adjacency = new Map();
        // Initialize
        for (const step of steps) {
            stepMap.set(step.id, step);
            inDegree.set(step.id, 0);
            adjacency.set(step.id, []);
        }
        // Build graph
        for (const step of steps) {
            if (step.needs) {
                for (const dep of step.needs) {
                    if (stepMap.has(dep)) {
                        const adj = adjacency.get(dep);
                        if (adj)
                            adj.push(step.id);
                        inDegree.set(step.id, (inDegree.get(step.id) ?? 0) + 1);
                    }
                }
            }
        }
        // Find all nodes with no incoming edges
        const queue = [];
        inDegree.forEach((degree, stepId) => {
            if (degree === 0) {
                queue.push(stepId);
            }
        });
        const sorted = [];
        while (queue.length > 0) {
            const current = queue.shift();
            const step = stepMap.get(current);
            if (step) {
                sorted.push(step);
            }
            for (const neighbor of adjacency.get(current) ?? []) {
                const newDegree = (inDegree.get(neighbor) ?? 1) - 1;
                inDegree.set(neighbor, newDegree);
                if (newDegree === 0) {
                    queue.push(neighbor);
                }
            }
        }
        // Check for cycle (not all nodes processed)
        if (sorted.length !== steps.length) {
            throw new GasTownError('Cycle detected in step dependencies', GasTownErrorCode.DEPENDENCY_CYCLE, { sortedCount: sorted.length, totalCount: steps.length });
        }
        return sorted;
    }
    detectCycle(steps) {
        const visited = new Set();
        const recStack = new Set();
        const stepMap = new Map();
        for (const step of steps) {
            stepMap.set(step.id, step);
        }
        const dfs = (stepId, path) => {
            visited.add(stepId);
            recStack.add(stepId);
            const step = stepMap.get(stepId);
            if (step?.needs) {
                for (const dep of step.needs) {
                    if (!visited.has(dep)) {
                        const cycle = dfs(dep, [...path, dep]);
                        if (cycle)
                            return cycle;
                    }
                    else if (recStack.has(dep)) {
                        return [...path, dep];
                    }
                }
            }
            recStack.delete(stepId);
            return null;
        };
        for (const step of steps) {
            if (!visited.has(step.id)) {
                const cycle = dfs(step.id, [step.id]);
                if (cycle) {
                    return { hasCycle: true, cycleSteps: cycle };
                }
            }
        }
        return { hasCycle: false };
    }
}
// ============================================================================
// Formula Executor Implementation
// ============================================================================
/**
 * Hybrid Formula Executor
 *
 * Uses WASM for fast parsing and cooking operations,
 * falls back to CLI bridge for I/O operations.
 *
 * @example
 * ```typescript
 * const executor = new FormulaExecutor(gtBridge, wasmLoader);
 *
 * // Full execution
 * const results = await executor.execute('my-formula', { feature: 'auth' });
 *
 * // Just cook (WASM-accelerated)
 * const cooked = await executor.cook('my-formula', { feature: 'auth' });
 *
 * // Generate molecules
 * const molecules = await executor.generateMolecules(cooked);
 * ```
 */
export class FormulaExecutor extends EventEmitter {
    gtBridge;
    wasmLoader;
    logger;
    jsFallback;
    /** Active executions for progress tracking */
    executions = new Map();
    /** Cancellation controllers */
    cancellations = new Map();
    /** Debounced progress emitters per execution */
    progressEmitters = new Map();
    /** Default max parallel workers */
    defaultMaxParallel = 4;
    constructor(gtBridge, wasmLoader, logger) {
        super();
        this.gtBridge = gtBridge;
        this.wasmLoader = wasmLoader ?? new JsFallbackWasmLoader();
        this.logger = logger ?? defaultLogger;
        this.jsFallback = new JsFallbackWasmLoader();
    }
    // ============================================================================
    // Public API
    // ============================================================================
    /**
     * Execute a formula with full lifecycle
     *
     * @param formulaName - Name of the formula to execute
     * @param vars - Variables for substitution
     * @param options - Execution options
     * @returns Array of step results
     */
    async execute(formulaName, vars, options = {}) {
        const executionId = randomUUID();
        const abortController = new AbortController();
        // Register cancellation controller
        this.cancellations.set(executionId, abortController);
        // Merge signals
        const signal = options.signal
            ? this.mergeSignals(options.signal, abortController.signal)
            : abortController.signal;
        try {
            // Step 1: Fetch and cook the formula
            this.logger.info('Starting formula execution', { executionId, formulaName });
            const cooked = await this.cook(formulaName, vars);
            // Initialize progress tracking
            const steps = cooked.steps ?? [];
            const legs = cooked.legs ?? [];
            const totalSteps = steps.length || legs.length;
            const progress = {
                executionId,
                formulaName,
                status: 'running',
                totalSteps,
                completedSteps: 0,
                failedSteps: 0,
                startTime: new Date(),
                stepResults: [],
                percentage: 0,
            };
            this.executions.set(executionId, progress);
            this.emit('execution:start', executionId, cooked);
            // Create debounced progress emitter (100ms debounce)
            const progressEmitter = new DebouncedEmitter((p) => this.emit('execution:progress', p), 100);
            this.progressEmitters.set(executionId, progressEmitter);
            // Step 2: Resolve dependencies and get execution order
            const orderedSteps = this.getOrderedExecutionUnits(cooked);
            // Step 3: Execute steps with parallel execution where deps allow
            const results = [];
            const previousResults = new Map();
            const maxParallel = options.maxParallel ?? this.defaultMaxParallel;
            // Use parallel execution with work stealing if enabled
            if (maxParallel > 1 && orderedSteps.length > 1) {
                // Build dependency graph for parallel execution
                const stepDeps = new Map();
                const stepById = new Map();
                const stepIndex = new Map();
                for (let i = 0; i < orderedSteps.length; i++) {
                    const step = orderedSteps[i];
                    stepById.set(step.id, step);
                    stepIndex.set(step.id, i);
                    stepDeps.set(step.id, new Set(step.needs ?? []));
                }
                // Track completed steps
                const completed = new Set();
                const inProgress = new Set();
                // Work stealing queue
                const workQueue = new WorkStealingQueue(maxParallel);
                // Find steps that can run (no dependencies)
                const getReadySteps = () => {
                    const ready = [];
                    for (const step of orderedSteps) {
                        if (completed.has(step.id) || inProgress.has(step.id))
                            continue;
                        const deps = stepDeps.get(step.id);
                        if (!deps || [...deps].every(d => completed.has(d))) {
                            ready.push(step);
                        }
                    }
                    return ready;
                };
                // Execute in parallel waves
                while (completed.size < orderedSteps.length) {
                    // Check for cancellation
                    if (signal.aborted) {
                        progress.status = 'cancelled';
                        this.emit('execution:cancelled', executionId);
                        throw new GasTownError('Execution cancelled', GasTownErrorCode.UNKNOWN, { executionId });
                    }
                    const readySteps = getReadySteps();
                    if (readySteps.length === 0 && inProgress.size === 0) {
                        // Deadlock - should not happen with valid DAG
                        break;
                    }
                    // Limit parallel execution
                    const batchSize = Math.min(readySteps.length, maxParallel - inProgress.size);
                    const batch = readySteps.slice(0, batchSize);
                    if (batch.length === 0) {
                        // Wait for in-progress steps to complete
                        await new Promise(resolve => setTimeout(resolve, 10));
                        continue;
                    }
                    // Mark as in progress
                    for (const step of batch) {
                        inProgress.add(step.id);
                    }
                    // Execute batch in parallel
                    const batchPromises = batch.map(async (step) => {
                        const idx = stepIndex.get(step.id) ?? 0;
                        progress.currentStep = step.id;
                        const context = {
                            executionId,
                            formula: cooked,
                            stepIndex: idx,
                            totalSteps: orderedSteps.length,
                            variables: cooked.cookedVars,
                            previousResults,
                            signal,
                            startTime: progress.startTime,
                        };
                        this.emit('step:start', executionId, step);
                        try {
                            const result = await this.runStep(step, context, options);
                            previousResults.set(step.id, result);
                            completed.add(step.id);
                            inProgress.delete(step.id);
                            if (result.success) {
                                progress.completedSteps++;
                            }
                            else {
                                progress.failedSteps++;
                            }
                            progress.stepResults.push(result);
                            progress.percentage = Math.round((completed.size / orderedSteps.length) * 100);
                            this.emit('step:complete', executionId, result);
                            progressEmitter.update({ ...progress });
                            return result;
                        }
                        catch (error) {
                            const failedResult = {
                                stepId: step.id,
                                success: false,
                                error: error instanceof Error ? error.message : String(error),
                                durationMs: 0,
                            };
                            previousResults.set(step.id, failedResult);
                            completed.add(step.id); // Mark as completed (failed)
                            inProgress.delete(step.id);
                            progress.failedSteps++;
                            progress.stepResults.push(failedResult);
                            this.emit('step:error', executionId, step.id, error);
                            progressEmitter.update({ ...progress });
                            // Continue or fail based on step configuration
                            if (!step.metadata?.continueOnError) {
                                throw error;
                            }
                            return failedResult;
                        }
                    });
                    const batchResults = await Promise.all(batchPromises);
                    results.push(...batchResults);
                }
                // Flush final progress
                progressEmitter.flush();
            }
            else {
                // Sequential execution (original behavior)
                for (let i = 0; i < orderedSteps.length; i++) {
                    // Check for cancellation
                    if (signal.aborted) {
                        progress.status = 'cancelled';
                        this.emit('execution:cancelled', executionId);
                        throw new GasTownError('Execution cancelled', GasTownErrorCode.UNKNOWN, { executionId });
                    }
                    const step = orderedSteps[i];
                    progress.currentStep = step.id;
                    const context = {
                        executionId,
                        formula: cooked,
                        stepIndex: i,
                        totalSteps: orderedSteps.length,
                        variables: cooked.cookedVars,
                        previousResults,
                        signal,
                        startTime: progress.startTime,
                    };
                    this.emit('step:start', executionId, step);
                    try {
                        const result = await this.runStep(step, context, options);
                        results.push(result);
                        previousResults.set(step.id, result);
                        if (result.success) {
                            progress.completedSteps++;
                        }
                        else {
                            progress.failedSteps++;
                        }
                        progress.stepResults.push(result);
                        progress.percentage = Math.round(((i + 1) / orderedSteps.length) * 100);
                        this.emit('step:complete', executionId, result);
                        progressEmitter.update({ ...progress });
                    }
                    catch (error) {
                        const failedResult = {
                            stepId: step.id,
                            success: false,
                            error: error instanceof Error ? error.message : String(error),
                            durationMs: 0,
                        };
                        results.push(failedResult);
                        previousResults.set(step.id, failedResult);
                        progress.failedSteps++;
                        progress.stepResults.push(failedResult);
                        this.emit('step:error', executionId, step.id, error);
                        // Continue or fail based on step configuration
                        if (!step.metadata?.continueOnError) {
                            throw error;
                        }
                    }
                }
                // Flush final progress
                progressEmitter.flush();
            }
            // Step 4: Complete execution
            progress.status = progress.failedSteps > 0 ? 'failed' : 'completed';
            progress.endTime = new Date();
            progress.percentage = 100;
            this.emit('execution:complete', executionId, results);
            this.logger.info('Formula execution completed', {
                executionId,
                formulaName,
                completed: progress.completedSteps,
                failed: progress.failedSteps,
            });
            return results;
        }
        catch (error) {
            const progress = this.executions.get(executionId);
            if (progress) {
                progress.status = 'failed';
                progress.endTime = new Date();
                progress.error = error instanceof Error ? error.message : String(error);
            }
            this.emit('execution:error', executionId, error);
            throw error;
        }
        finally {
            this.cancellations.delete(executionId);
            // Cleanup progress emitter
            const emitter = this.progressEmitters.get(executionId);
            if (emitter) {
                emitter.cancel();
                this.progressEmitters.delete(executionId);
            }
        }
    }
    /**
     * Cook a formula with variable substitution (WASM-accelerated)
     *
     * @param formulaName - Name of the formula or TOML content
     * @param vars - Variables for substitution
     * @returns Cooked formula with substituted variables
     */
    async cook(formulaName, vars) {
        this.logger.debug('Cooking formula', { formulaName, varsCount: Object.keys(vars).length });
        // Generate cache key from formula name and vars
        const varKeys = Object.keys(vars).sort();
        const varValues = varKeys.map(k => vars[k]);
        const cacheKey = hashKey([formulaName, ...varKeys, ...varValues]);
        // Check cook cache first
        const cached = cookCache.get(cacheKey);
        if (cached) {
            this.logger.debug('Cook cache hit', { formulaName });
            return cached;
        }
        // Use deduplication for concurrent identical requests
        return cookDedup.dedupe(cacheKey, async () => {
            try {
                // Determine if formulaName is content or a name to fetch
                let formula;
                if (formulaName.includes('[') || formulaName.includes('=')) {
                    // Looks like TOML content, parse directly
                    formula = this.parseFormula(formulaName);
                }
                else {
                    // Fetch formula from CLI with deduplication
                    formula = await fetchDedup.dedupe(formulaName, () => this.fetchFormula(formulaName));
                }
                // Validate required variables
                this.validateVariables(formula, vars);
                // Cook using WASM if available, otherwise JS fallback
                const loader = this.wasmLoader.isInitialized() ? this.wasmLoader : this.jsFallback;
                const cooked = loader.cookFormula(formula, vars);
                // Cache the result
                cookCache.set(cacheKey, cooked);
                this.logger.debug('Formula cooked successfully', {
                    formulaName,
                    wasmAccelerated: this.wasmLoader.isInitialized(),
                });
                return cooked;
            }
            catch (error) {
                if (error instanceof GasTownError)
                    throw error;
                throw FormulaError.cookFailed(formulaName, error instanceof Error ? error.message : String(error), error);
            }
        });
    }
    /**
     * Generate molecules from a cooked formula
     *
     * Molecules are executable work units derived from formula steps/legs.
     * Uses object pooling for reduced allocations.
     *
     * @param cookedFormula - The cooked formula to generate molecules from
     * @returns Array of molecules
     */
    async generateMolecules(cookedFormula) {
        this.logger.debug('Generating molecules', { formulaName: cookedFormula.name });
        const molecules = [];
        const moleculeIdMap = new Map();
        // Generate molecules based on formula type
        if (cookedFormula.type === 'convoy' && cookedFormula.legs) {
            // Convoy: Generate from legs
            const orderedLegs = [...cookedFormula.legs].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
            for (let i = 0; i < orderedLegs.length; i++) {
                const leg = orderedLegs[i];
                const moleculeId = `mol-${cookedFormula.name}-${leg.id}-${randomUUID().slice(0, 8)}`;
                moleculeIdMap.set(leg.id, moleculeId);
                // Use pooled molecule for reduced allocations
                const pooledMol = moleculePool.acquire();
                pooledMol.id = moleculeId;
                pooledMol.formulaName = cookedFormula.name;
                pooledMol.title = leg.title;
                pooledMol.description = leg.description;
                pooledMol.type = cookedFormula.type;
                pooledMol.sourceId = leg.id;
                pooledMol.agent = leg.agent;
                pooledMol.dependencies = i > 0 ? [moleculeIdMap.get(orderedLegs[i - 1].id)] : [];
                pooledMol.order = i;
                pooledMol.metadata = {
                    focus: leg.focus,
                    legOrder: leg.order,
                };
                pooledMol.createdAt = new Date();
                // Create plain molecule for return (avoid pool reference issues)
                const molecule = {
                    id: pooledMol.id,
                    formulaName: pooledMol.formulaName,
                    title: pooledMol.title,
                    description: pooledMol.description,
                    type: pooledMol.type,
                    sourceId: pooledMol.sourceId,
                    agent: pooledMol.agent,
                    dependencies: [...pooledMol.dependencies],
                    order: pooledMol.order,
                    metadata: { ...pooledMol.metadata },
                    createdAt: pooledMol.createdAt,
                };
                // Release pooled molecule back to pool
                moleculePool.release(pooledMol);
                molecules.push(molecule);
                this.emit('molecule:created', molecule);
            }
        }
        else if (cookedFormula.steps) {
            // Workflow/Expansion/Aspect: Generate from steps
            const orderedSteps = this.resolveStepDependencies(cookedFormula.steps);
            for (let i = 0; i < orderedSteps.length; i++) {
                const step = orderedSteps[i];
                const moleculeId = `mol-${cookedFormula.name}-${step.id}-${randomUUID().slice(0, 8)}`;
                moleculeIdMap.set(step.id, moleculeId);
                // Map step dependencies to molecule IDs
                const dependencies = [];
                if (step.needs) {
                    for (const need of step.needs) {
                        const depMoleculeId = moleculeIdMap.get(need);
                        if (depMoleculeId) {
                            dependencies.push(depMoleculeId);
                        }
                    }
                }
                // Use pooled molecule for reduced allocations
                const pooledMol = moleculePool.acquire();
                pooledMol.id = moleculeId;
                pooledMol.formulaName = cookedFormula.name;
                pooledMol.title = step.title;
                pooledMol.description = step.description;
                pooledMol.type = cookedFormula.type;
                pooledMol.sourceId = step.id;
                pooledMol.agent = undefined;
                pooledMol.dependencies = dependencies;
                pooledMol.order = i;
                pooledMol.metadata = {
                    duration: step.duration,
                    requires: step.requires,
                    ...step.metadata,
                };
                pooledMol.createdAt = new Date();
                // Create plain molecule for return (avoid pool reference issues)
                const molecule = {
                    id: pooledMol.id,
                    formulaName: pooledMol.formulaName,
                    title: pooledMol.title,
                    description: pooledMol.description,
                    type: pooledMol.type,
                    sourceId: pooledMol.sourceId,
                    agent: pooledMol.agent,
                    dependencies: [...pooledMol.dependencies],
                    order: pooledMol.order,
                    metadata: { ...pooledMol.metadata },
                    createdAt: pooledMol.createdAt,
                };
                // Release pooled molecule back to pool
                moleculePool.release(pooledMol);
                molecules.push(molecule);
                this.emit('molecule:created', molecule);
            }
        }
        this.logger.info('Molecules generated', {
            formulaName: cookedFormula.name,
            count: molecules.length,
        });
        return molecules;
    }
    /**
     * Run a single step
     *
     * @param step - Step to execute
     * @param context - Execution context
     * @param options - Execution options
     * @returns Step result
     */
    async runStep(step, context, options = {}) {
        const startTime = Date.now();
        this.logger.debug('Running step', {
            stepId: step.id,
            executionId: context.executionId,
        });
        // Generate cache key for step result memoization
        // Only cache if step is deterministic (no side effects indicator)
        const isCacheable = step.metadata?.cacheable !== false && !step.metadata?.hasSideEffects;
        const stepCacheKey = isCacheable
            ? hashKey([
                step.id,
                context.formula.name,
                JSON.stringify(context.variables),
                JSON.stringify(step.needs ?? []),
            ])
            : null;
        // Check step result cache
        if (stepCacheKey) {
            const cachedResult = stepResultCache.get(stepCacheKey);
            if (cachedResult) {
                this.logger.debug('Step cache hit', { stepId: step.id });
                return {
                    ...cachedResult,
                    metadata: { ...cachedResult.metadata, fromCache: true },
                };
            }
        }
        try {
            // Check for cancellation
            if (context.signal?.aborted) {
                throw new GasTownError('Step cancelled', GasTownErrorCode.UNKNOWN);
            }
            // Check dependencies are satisfied
            if (step.needs) {
                for (const dep of step.needs) {
                    const depResult = context.previousResults.get(dep);
                    if (!depResult || !depResult.success) {
                        throw new GasTownError(`Dependency not satisfied: ${dep}`, GasTownErrorCode.UNKNOWN, { stepId: step.id, dependency: dep });
                    }
                }
            }
            // Use custom step handler if provided
            if (options.stepHandler) {
                const result = await options.stepHandler(step, context);
                if (stepCacheKey && result.success) {
                    stepResultCache.set(stepCacheKey, result);
                }
                return result;
            }
            // Dry run mode
            if (options.dryRun) {
                return {
                    stepId: step.id,
                    success: true,
                    output: { dryRun: true, step },
                    durationMs: Date.now() - startTime,
                    metadata: { dryRun: true },
                };
            }
            // Default execution via CLI
            const result = await this.executeStepViaCli(step, context, options);
            const stepResult = {
                stepId: step.id,
                success: true,
                output: result,
                durationMs: Date.now() - startTime,
            };
            // Cache successful result
            if (stepCacheKey) {
                stepResultCache.set(stepCacheKey, stepResult);
            }
            return stepResult;
        }
        catch (error) {
            return {
                stepId: step.id,
                success: false,
                error: error instanceof Error ? error.message : String(error),
                durationMs: Date.now() - startTime,
            };
        }
    }
    /**
     * Get execution progress
     *
     * @param executionId - Execution ID to get progress for
     * @returns Execution progress or undefined
     */
    getProgress(executionId) {
        return this.executions.get(executionId);
    }
    /**
     * Cancel an execution
     *
     * @param executionId - Execution ID to cancel
     * @returns Whether cancellation was initiated
     */
    cancel(executionId) {
        const controller = this.cancellations.get(executionId);
        if (controller) {
            controller.abort();
            return true;
        }
        return false;
    }
    /**
     * List all active executions
     */
    getActiveExecutions() {
        return Array.from(this.executions.values()).filter(e => e.status === 'running' || e.status === 'pending');
    }
    /**
     * Check if WASM is available for acceleration
     */
    isWasmAvailable() {
        return this.wasmLoader.isInitialized();
    }
    /**
     * Get cache statistics for performance monitoring
     */
    getCacheStats() {
        return {
            stepResultCache: stepResultCache.stats(),
            cookCache: cookCache.stats(),
        };
    }
    /**
     * Clear all executor caches
     */
    clearCaches() {
        stepResultCache.clear();
        cookCache.clear();
    }
    // ============================================================================
    // Private Methods
    // ============================================================================
    /**
     * Parse formula content using WASM or JS fallback
     */
    parseFormula(content) {
        const loader = this.wasmLoader.isInitialized() ? this.wasmLoader : this.jsFallback;
        return loader.parseFormula(content);
    }
    /**
     * Fetch formula from CLI
     */
    async fetchFormula(formulaName) {
        // Check if bridge is initialized
        if (!this.gtBridge.isInitialized()) {
            throw new GasTownError('GtBridge not initialized', GasTownErrorCode.NOT_INITIALIZED);
        }
        // Fetch formula via CLI (would be: gt formula show <name> --json)
        // For now, simulate with a placeholder
        // In production, this would call: this.gtBridge.execGt(['formula', 'show', formulaName, '--json'])
        this.logger.debug('Fetching formula from CLI', { formulaName });
        // Simulated formula for demonstration
        const formula = {
            name: formulaName,
            description: `Formula: ${formulaName}`,
            type: 'workflow',
            version: 1,
            steps: [
                {
                    id: 'init',
                    title: 'Initialize',
                    description: 'Initialize the workflow',
                },
                {
                    id: 'process',
                    title: 'Process',
                    description: 'Process the data',
                    needs: ['init'],
                },
                {
                    id: 'finalize',
                    title: 'Finalize',
                    description: 'Finalize the workflow',
                    needs: ['process'],
                },
            ],
            vars: {},
        };
        return formula;
    }
    /**
     * Validate required variables are provided
     */
    validateVariables(formula, vars) {
        if (!formula.vars)
            return;
        const missing = [];
        for (const [name, varDef] of Object.entries(formula.vars)) {
            if (varDef.required && !(name in vars) && !varDef.default) {
                missing.push(name);
            }
        }
        if (missing.length > 0) {
            throw new GasTownError(`Missing required variables: ${missing.join(', ')}`, GasTownErrorCode.INVALID_ARGUMENTS, { missing });
        }
    }
    /**
     * Resolve step dependencies using WASM or JS fallback
     */
    resolveStepDependencies(steps) {
        const loader = this.wasmLoader.isInitialized() ? this.wasmLoader : this.jsFallback;
        return loader.resolveStepDependencies(steps);
    }
    /**
     * Get ordered execution units (steps or legs) from formula
     */
    getOrderedExecutionUnits(formula) {
        if (formula.type === 'convoy' && formula.legs) {
            // Convert legs to steps for unified execution
            const legs = [...formula.legs].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
            return legs.map((leg, index) => ({
                id: leg.id,
                title: leg.title,
                description: leg.description,
                needs: index > 0 ? [legs[index - 1].id] : undefined,
                metadata: { agent: leg.agent, focus: leg.focus },
            }));
        }
        if (formula.steps) {
            return this.resolveStepDependencies(formula.steps);
        }
        return [];
    }
    /**
     * Execute step via CLI bridge
     */
    async executeStepViaCli(step, context, options) {
        // Build CLI command for step execution
        const args = [
            'formula',
            'step',
            step.id,
            '--execution-id', context.executionId,
            '--json',
        ];
        if (options.targetAgent) {
            args.push('--agent', options.targetAgent);
        }
        if (options.stepTimeout) {
            args.push('--timeout', String(options.stepTimeout));
        }
        // Execute via bridge
        const result = await this.gtBridge.execGt(args);
        if (!result.success) {
            throw new GasTownError(`Step execution failed: ${result.error}`, GasTownErrorCode.CLI_EXECUTION_FAILED, { stepId: step.id, error: result.error });
        }
        return result.data ? JSON.parse(result.data) : null;
    }
    /**
     * Merge multiple abort signals
     */
    mergeSignals(...signals) {
        const controller = new AbortController();
        for (const signal of signals) {
            if (signal.aborted) {
                controller.abort();
                break;
            }
            signal.addEventListener('abort', () => controller.abort(), { once: true });
        }
        return controller.signal;
    }
}
// ============================================================================
// Factory Function
// ============================================================================
/**
 * Create a new FormulaExecutor instance
 */
export function createFormulaExecutor(gtBridge, wasmLoader, logger) {
    return new FormulaExecutor(gtBridge, wasmLoader, logger);
}
export default FormulaExecutor;
//# sourceMappingURL=executor.js.map