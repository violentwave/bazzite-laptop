/**
 * GUPP Adapter - Gastown Universal Propulsion Principle
 *
 * Bridge between GUPP work tracking and Claude Flow session management.
 * GUPP principle: "If work is on your hook, YOU MUST RUN IT"
 *
 * This adapter provides:
 * - Hook registration for session lifecycle events
 * - Automatic work resumption after crash/restart
 * - Work item tracking and state persistence
 *
 * @module gastown-bridge/gupp/adapter
 * @version 0.1.0
 */
import { createEmptyState, createSession, createHookedWorkItem, saveState, loadState, saveStateToAgentDB, loadStateFromAgentDB, mergeStates, getPendingWork, getWorkNeedingResumption, touchSession, endSession, DEFAULT_STATE_PATH, } from './state.js';
// ============================================================================
// GUPP Adapter Implementation
// ============================================================================
/**
 * GUPP Adapter - Bridge between Gas Town work tracking and Claude Flow sessions
 *
 * Implements the GUPP principle: "If work is on your hook, YOU MUST RUN IT"
 *
 * @example
 * ```typescript
 * const adapter = new GuppAdapter(sessionManager, gtBridge, {
 *   autoResume: true,
 *   useAgentDB: true,
 * });
 *
 * await adapter.registerHooks();
 *
 * adapter.onSessionStart((sessionId, restored) => {
 *   console.log(`Session ${sessionId} started (restored: ${restored})`);
 * });
 *
 * adapter.onWorkSlung((work) => {
 *   console.log(`Work slung: ${work.title}`);
 * });
 * ```
 */
export class GuppAdapter {
    sessionManager;
    gtBridge;
    config;
    state;
    initialized = false;
    // Hook callbacks
    sessionStartCallbacks = [];
    sessionEndCallbacks = [];
    workSlungCallbacks = [];
    workCompleteCallbacks = [];
    // Internal handlers (bound for proper removal)
    boundSessionStartHandler;
    boundSessionEndHandler;
    crashCheckTimer = null;
    constructor(sessionManager, gtBridge, config) {
        this.sessionManager = sessionManager;
        this.gtBridge = gtBridge;
        this.config = {
            statePath: config?.statePath ?? DEFAULT_STATE_PATH,
            useAgentDB: config?.useAgentDB ?? false,
            agentDB: config?.agentDB ?? undefined,
            autoResume: config?.autoResume ?? true,
            crashCheckInterval: config?.crashCheckInterval ?? 30000,
            sessionTimeout: config?.sessionTimeout ?? 60000,
            owner: config?.owner ?? 'gupp-adapter',
        };
        this.state = createEmptyState();
        // Bind handlers
        this.boundSessionStartHandler = this.handleSessionStart.bind(this);
        this.boundSessionEndHandler = this.handleSessionEnd.bind(this);
    }
    // ============================================================================
    // Initialization
    // ============================================================================
    /**
     * Register hooks with the session manager
     */
    async registerHooks() {
        if (this.initialized) {
            return;
        }
        // Load existing state
        await this.loadPersistedState();
        // Register session lifecycle hooks
        this.sessionManager.on('session-start', this.boundSessionStartHandler);
        this.sessionManager.on('session-end', this.boundSessionEndHandler);
        // Start crash detection if enabled
        if (this.config.crashCheckInterval > 0) {
            this.startCrashDetection();
        }
        this.initialized = true;
    }
    /**
     * Unregister hooks and cleanup
     */
    async unregisterHooks() {
        if (!this.initialized) {
            return;
        }
        // Remove session hooks
        this.sessionManager.off('session-start', this.boundSessionStartHandler);
        this.sessionManager.off('session-end', this.boundSessionEndHandler);
        // Stop crash detection
        this.stopCrashDetection();
        // Persist final state
        await this.persistState(this.state);
        this.initialized = false;
    }
    // ============================================================================
    // Hook Registration
    // ============================================================================
    /**
     * Register callback for session start events
     */
    onSessionStart(callback) {
        this.sessionStartCallbacks.push(callback);
    }
    /**
     * Register callback for session end events
     */
    onSessionEnd(callback) {
        this.sessionEndCallbacks.push(callback);
    }
    /**
     * Register callback for when work is slung (hooked)
     */
    onWorkSlung(callback) {
        this.workSlungCallbacks.push(callback);
    }
    /**
     * Register callback for work completion
     */
    onWorkComplete(callback) {
        this.workCompleteCallbacks.push(callback);
    }
    // ============================================================================
    // State Persistence
    // ============================================================================
    /**
     * Persist current state to storage
     */
    async persistState(state) {
        // Always save to disk
        await saveState(state, this.config.statePath);
        // Optionally save to AgentDB
        if (this.config.useAgentDB && this.config.agentDB) {
            await saveStateToAgentDB(state, this.config.agentDB);
        }
    }
    /**
     * Restore state from storage
     */
    async restoreState() {
        // Load from disk
        const diskState = await loadState(this.config.statePath);
        // If AgentDB is enabled, merge with AgentDB state
        if (this.config.useAgentDB && this.config.agentDB) {
            const agentDBState = await loadStateFromAgentDB(this.config.agentDB);
            return mergeStates(diskState, agentDBState);
        }
        return diskState;
    }
    // ============================================================================
    // Work Management (GUPP Principle)
    // ============================================================================
    /**
     * Get all work currently "on the hook"
     * GUPP principle: If work is on your hook, YOU MUST RUN IT
     */
    getHookedWork() {
        return [...this.state.hookedWork];
    }
    /**
     * Get pending work that needs to be run
     */
    getPendingWork() {
        return getPendingWork(this.state);
    }
    /**
     * Hook new work (sling it)
     */
    async hookWork(id, title, options) {
        const workItem = createHookedWorkItem(id, title, options);
        // Add to state
        this.state = {
            ...this.state,
            hookedWork: [...this.state.hookedWork, workItem],
            updatedAt: new Date(),
        };
        // Persist state
        await this.persistState(this.state);
        // Notify callbacks
        await this.notifyWorkSlung(workItem);
        return workItem;
    }
    /**
     * Update work item status
     */
    async updateWorkStatus(id, status, progress, error) {
        const index = this.state.hookedWork.findIndex((w) => w.id === id);
        if (index === -1) {
            return null;
        }
        const updated = {
            ...this.state.hookedWork[index],
            status,
            progress: progress ?? this.state.hookedWork[index].progress,
            error,
            updatedAt: new Date(),
        };
        const newHookedWork = [...this.state.hookedWork];
        newHookedWork[index] = updated;
        this.state = {
            ...this.state,
            hookedWork: newHookedWork,
            updatedAt: new Date(),
        };
        await this.persistState(this.state);
        // If completed or failed, notify
        if (status === 'completed' || status === 'failed') {
            await this.notifyWorkComplete(updated, status === 'completed');
        }
        return updated;
    }
    /**
     * Complete a work item
     */
    async completeWork(id, result) {
        await this.updateWorkStatus(id, 'completed', 100);
    }
    /**
     * Fail a work item
     */
    async failWork(id, error) {
        await this.updateWorkStatus(id, 'failed', undefined, error);
    }
    /**
     * Remove work from the hook
     */
    async unhookWork(id) {
        const index = this.state.hookedWork.findIndex((w) => w.id === id);
        if (index === -1) {
            return false;
        }
        this.state = {
            ...this.state,
            hookedWork: this.state.hookedWork.filter((w) => w.id !== id),
            updatedAt: new Date(),
        };
        await this.persistState(this.state);
        return true;
    }
    // ============================================================================
    // Work Resumption (GUPP Principle Implementation)
    // ============================================================================
    /**
     * Resume work after session restore
     * GUPP principle: If work is on your hook, YOU MUST RUN IT
     */
    async resumeWork() {
        const workToResume = getWorkNeedingResumption(this.state);
        const result = {
            resumed: 0,
            failed: [],
            skipped: 0,
        };
        for (const work of workToResume) {
            try {
                // Check if work is still valid (e.g., bead/convoy still exists)
                const isValid = await this.validateWorkItem(work);
                if (!isValid) {
                    // Mark as failed due to invalid state
                    await this.updateWorkStatus(work.id, 'failed', undefined, 'Work item no longer valid after restart');
                    result.failed.push(work);
                    continue;
                }
                // Resume the work item
                await this.updateWorkStatus(work.id, 'active', work.progress);
                result.resumed++;
                // Notify callbacks about resumption
                await this.notifyWorkSlung(work);
            }
            catch (error) {
                result.failed.push(work);
                await this.updateWorkStatus(work.id, 'failed', undefined, `Failed to resume: ${error instanceof Error ? error.message : 'Unknown error'}`);
            }
        }
        return result;
    }
    // ============================================================================
    // Private Methods
    // ============================================================================
    async loadPersistedState() {
        this.state = await this.restoreState();
    }
    async handleSessionStart() {
        const sessionId = this.sessionManager.getSessionId();
        if (!sessionId) {
            return;
        }
        const isRestored = !!this.state.session && this.state.session.id === sessionId;
        // Update state with new/restored session
        if (isRestored) {
            this.state = touchSession(this.state);
        }
        else {
            this.state = {
                ...this.state,
                session: createSession(sessionId, this.config.owner),
                updatedAt: new Date(),
            };
        }
        await this.persistState(this.state);
        // Auto-resume work if enabled and session was restored
        if (this.config.autoResume && isRestored) {
            const resumeResult = await this.resumeWork();
            console.log(`[GUPP] Resumed ${resumeResult.resumed} work items, ` +
                `${resumeResult.failed.length} failed, ${resumeResult.skipped} skipped`);
        }
        // Notify callbacks
        await this.notifySessionStart(sessionId, isRestored);
    }
    async handleSessionEnd() {
        const sessionId = this.state.session?.id;
        if (!sessionId) {
            return;
        }
        this.state = endSession(this.state);
        await this.persistState(this.state);
        // Notify callbacks
        await this.notifySessionEnd(sessionId, true);
    }
    startCrashDetection() {
        this.crashCheckTimer = setInterval(async () => {
            await this.checkForCrash();
        }, this.config.crashCheckInterval);
    }
    stopCrashDetection() {
        if (this.crashCheckTimer) {
            clearInterval(this.crashCheckTimer);
            this.crashCheckTimer = null;
        }
    }
    async checkForCrash() {
        if (!this.state.session?.active) {
            return;
        }
        const now = Date.now();
        const lastActive = this.state.session.lastActiveAt.getTime();
        const elapsed = now - lastActive;
        if (elapsed > this.config.sessionTimeout) {
            // Session appears to have crashed
            console.warn('[GUPP] Session timeout detected - possible crash');
            // Update recovery metadata
            this.state = {
                ...this.state,
                recovery: {
                    ...this.state.recovery,
                    lastCrash: new Date(),
                    crashCount: (this.state.recovery?.crashCount ?? 0) + 1,
                    autoRecoverEnabled: this.state.recovery?.autoRecoverEnabled ?? true,
                },
                updatedAt: new Date(),
            };
            await this.persistState(this.state);
        }
        // Touch session to indicate we're still alive
        this.state = touchSession(this.state);
    }
    async validateWorkItem(work) {
        // If work is associated with a bead, verify it still exists
        if (work.beadId) {
            try {
                // Use GT bridge to verify bead exists
                // This is a simplified check - full implementation would query GT
                return true; // Assume valid for now
            }
            catch {
                return false;
            }
        }
        // If work is associated with a convoy, verify it's still active
        if (work.convoyId) {
            const convoy = this.state.convoys.find((c) => c.id === work.convoyId);
            if (!convoy || convoy.status === 'landed' || convoy.status === 'failed') {
                return false;
            }
        }
        return true;
    }
    // ============================================================================
    // Callback Notifications
    // ============================================================================
    async notifySessionStart(sessionId, restored) {
        for (const callback of this.sessionStartCallbacks) {
            try {
                await callback(sessionId, restored);
            }
            catch (error) {
                console.error('[GUPP] Session start callback error:', error);
            }
        }
    }
    async notifySessionEnd(sessionId, graceful) {
        for (const callback of this.sessionEndCallbacks) {
            try {
                await callback(sessionId, graceful);
            }
            catch (error) {
                console.error('[GUPP] Session end callback error:', error);
            }
        }
    }
    async notifyWorkSlung(work) {
        for (const callback of this.workSlungCallbacks) {
            try {
                await callback(work);
            }
            catch (error) {
                console.error('[GUPP] Work slung callback error:', error);
            }
        }
    }
    async notifyWorkComplete(work, success, result) {
        for (const callback of this.workCompleteCallbacks) {
            try {
                await callback(work, success, result);
            }
            catch (error) {
                console.error('[GUPP] Work complete callback error:', error);
            }
        }
    }
    // ============================================================================
    // Public Accessors
    // ============================================================================
    /**
     * Get current state (read-only)
     */
    getState() {
        return this.state;
    }
    /**
     * Get current session info
     */
    getSession() {
        return this.state.session;
    }
    /**
     * Check if adapter is initialized
     */
    isInitialized() {
        return this.initialized;
    }
    /**
     * Get active convoys
     */
    getConvoys() {
        return [...this.state.convoys];
    }
    /**
     * Add a convoy to track
     */
    async addConvoy(convoy) {
        this.state = {
            ...this.state,
            convoys: [...this.state.convoys, convoy],
            updatedAt: new Date(),
        };
        await this.persistState(this.state);
    }
    /**
     * Update a convoy
     */
    async updateConvoy(convoyId, updates) {
        const index = this.state.convoys.findIndex((c) => c.id === convoyId);
        if (index === -1) {
            return false;
        }
        const updated = {
            ...this.state.convoys[index],
            ...updates,
        };
        const newConvoys = [...this.state.convoys];
        newConvoys[index] = updated;
        this.state = {
            ...this.state,
            convoys: newConvoys,
            updatedAt: new Date(),
        };
        await this.persistState(this.state);
        return true;
    }
}
// ============================================================================
// Factory Function
// ============================================================================
/**
 * Create a GUPP adapter instance
 */
export function createGuppAdapter(sessionManager, gtBridge, config) {
    return new GuppAdapter(sessionManager, gtBridge, config);
}
export default GuppAdapter;
//# sourceMappingURL=adapter.js.map