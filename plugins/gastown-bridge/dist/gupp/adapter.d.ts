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
import type { GtBridge } from '../bridges/gt-bridge.js';
import type { Convoy } from '../types.js';
import { type GuppState, type HookedWorkItem, type SessionInfo, type WorkItemStatus, type AgentDBInterface } from './state.js';
/**
 * Session manager interface (Claude Flow compatible)
 */
export interface SessionManager {
    /** Get current session ID */
    getSessionId(): string | null;
    /** Check if session is active */
    isActive(): boolean;
    /** Start a new session */
    startSession(id?: string): Promise<string>;
    /** End the current session */
    endSession(): Promise<void>;
    /** Restore a previous session */
    restoreSession(id: string): Promise<boolean>;
    /** Register a hook for session events */
    on(event: string, handler: (...args: unknown[]) => void): void;
    /** Remove a hook */
    off(event: string, handler: (...args: unknown[]) => void): void;
}
/**
 * Hook callback types
 */
export type SessionStartCallback = (sessionId: string, restored: boolean) => void | Promise<void>;
export type SessionEndCallback = (sessionId: string, graceful: boolean) => void | Promise<void>;
export type WorkSlungCallback = (workItem: HookedWorkItem) => void | Promise<void>;
export type WorkCompleteCallback = (workItem: HookedWorkItem, success: boolean, result?: unknown) => void | Promise<void>;
/**
 * GUPP Adapter configuration
 */
export interface GuppAdapterConfig {
    /** Path to state file for disk persistence */
    statePath?: string;
    /** Enable AgentDB persistence */
    useAgentDB?: boolean;
    /** AgentDB interface */
    agentDB?: AgentDBInterface;
    /** Auto-resume work on session restore */
    autoResume?: boolean;
    /** Check interval for crashed sessions (ms) */
    crashCheckInterval?: number;
    /** Session timeout for crash detection (ms) */
    sessionTimeout?: number;
    /** Owner identifier for this adapter instance */
    owner?: string;
}
/**
 * Work resumption result
 */
export interface ResumptionResult {
    /** Number of work items resumed */
    resumed: number;
    /** Work items that failed to resume */
    failed: HookedWorkItem[];
    /** Work items that were skipped (already complete) */
    skipped: number;
}
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
export declare class GuppAdapter {
    private sessionManager;
    private gtBridge;
    private config;
    private state;
    private initialized;
    private sessionStartCallbacks;
    private sessionEndCallbacks;
    private workSlungCallbacks;
    private workCompleteCallbacks;
    private boundSessionStartHandler;
    private boundSessionEndHandler;
    private crashCheckTimer;
    constructor(sessionManager: SessionManager, gtBridge: GtBridge, config?: GuppAdapterConfig);
    /**
     * Register hooks with the session manager
     */
    registerHooks(): Promise<void>;
    /**
     * Unregister hooks and cleanup
     */
    unregisterHooks(): Promise<void>;
    /**
     * Register callback for session start events
     */
    onSessionStart(callback: SessionStartCallback): void;
    /**
     * Register callback for session end events
     */
    onSessionEnd(callback: SessionEndCallback): void;
    /**
     * Register callback for when work is slung (hooked)
     */
    onWorkSlung(callback: WorkSlungCallback): void;
    /**
     * Register callback for work completion
     */
    onWorkComplete(callback: WorkCompleteCallback): void;
    /**
     * Persist current state to storage
     */
    persistState(state: GuppState): Promise<void>;
    /**
     * Restore state from storage
     */
    restoreState(): Promise<GuppState>;
    /**
     * Get all work currently "on the hook"
     * GUPP principle: If work is on your hook, YOU MUST RUN IT
     */
    getHookedWork(): HookedWorkItem[];
    /**
     * Get pending work that needs to be run
     */
    getPendingWork(): HookedWorkItem[];
    /**
     * Hook new work (sling it)
     */
    hookWork(id: string, title: string, options?: Partial<Omit<HookedWorkItem, 'id' | 'title' | 'hookedAt' | 'updatedAt'>>): Promise<HookedWorkItem>;
    /**
     * Update work item status
     */
    updateWorkStatus(id: string, status: WorkItemStatus, progress?: number, error?: string): Promise<HookedWorkItem | null>;
    /**
     * Complete a work item
     */
    completeWork(id: string, result?: unknown): Promise<void>;
    /**
     * Fail a work item
     */
    failWork(id: string, error: string): Promise<void>;
    /**
     * Remove work from the hook
     */
    unhookWork(id: string): Promise<boolean>;
    /**
     * Resume work after session restore
     * GUPP principle: If work is on your hook, YOU MUST RUN IT
     */
    resumeWork(): Promise<ResumptionResult>;
    private loadPersistedState;
    private handleSessionStart;
    private handleSessionEnd;
    private startCrashDetection;
    private stopCrashDetection;
    private checkForCrash;
    private validateWorkItem;
    private notifySessionStart;
    private notifySessionEnd;
    private notifyWorkSlung;
    private notifyWorkComplete;
    /**
     * Get current state (read-only)
     */
    getState(): Readonly<GuppState>;
    /**
     * Get current session info
     */
    getSession(): SessionInfo | undefined;
    /**
     * Check if adapter is initialized
     */
    isInitialized(): boolean;
    /**
     * Get active convoys
     */
    getConvoys(): Convoy[];
    /**
     * Add a convoy to track
     */
    addConvoy(convoy: Convoy): Promise<void>;
    /**
     * Update a convoy
     */
    updateConvoy(convoyId: string, updates: Partial<Convoy>): Promise<boolean>;
}
/**
 * Create a GUPP adapter instance
 */
export declare function createGuppAdapter(sessionManager: SessionManager, gtBridge: GtBridge, config?: GuppAdapterConfig): GuppAdapter;
export default GuppAdapter;
//# sourceMappingURL=adapter.d.ts.map