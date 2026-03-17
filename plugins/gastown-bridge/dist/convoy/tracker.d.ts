/**
 * Convoy Tracker
 *
 * Manages convoy lifecycle including creation, modification, progress
 * tracking, and completion. Convoys are work-order groups that track
 * related beads (issues) through their lifecycle.
 *
 * Features:
 * - Create and manage convoy groups
 * - Add/remove beads to convoys
 * - Track progress and status changes
 * - Event emission for status transitions
 * - Integration with bd-bridge for bead operations
 *
 * @module gastown-bridge/convoy/tracker
 */
import { EventEmitter } from 'events';
import type { Convoy, ConvoyStatus, ConvoyProgress } from '../types.js';
import { BdBridge } from '../bridges/bd-bridge.js';
/**
 * Convoy event types
 */
export type ConvoyEventType = 'convoy:created' | 'convoy:started' | 'convoy:progressed' | 'convoy:completed' | 'convoy:cancelled' | 'convoy:paused' | 'convoy:resumed' | 'convoy:issue:added' | 'convoy:issue:removed' | 'convoy:issue:updated';
/**
 * Convoy event payload
 */
export interface ConvoyEvent {
    /** Event type */
    type: ConvoyEventType;
    /** Convoy ID */
    convoyId: string;
    /** Convoy name */
    convoyName: string;
    /** Event timestamp */
    timestamp: Date;
    /** Previous status (for status change events) */
    previousStatus?: ConvoyStatus;
    /** Current status */
    status: ConvoyStatus;
    /** Progress at time of event */
    progress: ConvoyProgress;
    /** Issue IDs affected (for issue events) */
    issues?: string[];
    /** Cancellation reason (for cancelled events) */
    reason?: string;
    /** Additional metadata */
    metadata?: Record<string, unknown>;
}
/**
 * Convoy tracker configuration
 */
export interface ConvoyTrackerConfig {
    /** BD bridge instance for bead operations */
    bdBridge: BdBridge;
    /** Auto-update progress on issue changes */
    autoUpdateProgress?: boolean;
    /** Progress update interval in milliseconds */
    progressUpdateInterval?: number;
    /** Enable persistent storage */
    persistConvoys?: boolean;
    /** Storage path for convoy data */
    storagePath?: string;
}
/**
 * Logger interface
 */
export interface ConvoyLogger {
    debug: (msg: string, meta?: Record<string, unknown>) => void;
    info: (msg: string, meta?: Record<string, unknown>) => void;
    warn: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
}
/**
 * Convoy Tracker
 *
 * Manages convoy lifecycle and tracks progress of grouped work.
 *
 * @example
 * ```typescript
 * const tracker = new ConvoyTracker({
 *   bdBridge: await createBdBridge().initialize(),
 * });
 *
 * // Create a convoy
 * const convoy = await tracker.create(
 *   'Sprint 1',
 *   ['gt-abc12', 'gt-def34', 'gt-ghi56'],
 *   'First sprint tasks'
 * );
 *
 * // Monitor progress
 * tracker.on('convoy:progressed', (event) => {
 *   console.log(`Progress: ${event.progress.closed}/${event.progress.total}`);
 * });
 *
 * // Check status
 * const status = await tracker.getStatus(convoy.id);
 * ```
 */
export declare class ConvoyTracker extends EventEmitter {
    private bdBridge;
    private convoys;
    private logger;
    private config;
    private progressTimers;
    constructor(config: ConvoyTrackerConfig, logger?: ConvoyLogger);
    /**
     * Create a new convoy
     *
     * @param name - Convoy name
     * @param issues - Issue IDs to include
     * @param description - Optional description
     * @returns Created convoy
     */
    create(name: string, issues: string[], description?: string): Promise<Convoy>;
    /**
     * Add issues to an existing convoy
     *
     * @param convoyId - Convoy ID
     * @param issues - Issue IDs to add
     * @returns Updated convoy
     */
    addIssues(convoyId: string, issues: string[]): Promise<Convoy>;
    /**
     * Remove issues from a convoy
     *
     * @param convoyId - Convoy ID
     * @param issues - Issue IDs to remove
     * @returns Updated convoy
     */
    removeIssues(convoyId: string, issues: string[]): Promise<Convoy>;
    /**
     * Get convoy status
     *
     * @param convoyId - Convoy ID
     * @returns Convoy with updated progress
     */
    getStatus(convoyId: string): Promise<Convoy>;
    /**
     * Mark convoy as complete
     *
     * @param convoyId - Convoy ID
     * @returns Completed convoy
     */
    complete(convoyId: string): Promise<Convoy>;
    /**
     * Cancel a convoy
     *
     * @param convoyId - Convoy ID
     * @param reason - Cancellation reason
     * @returns Cancelled convoy
     */
    cancel(convoyId: string, reason?: string): Promise<Convoy>;
    /**
     * Pause a convoy
     *
     * @param convoyId - Convoy ID
     * @returns Paused convoy
     */
    pause(convoyId: string): Promise<Convoy>;
    /**
     * Resume a paused convoy
     *
     * @param convoyId - Convoy ID
     * @returns Resumed convoy
     */
    resume(convoyId: string): Promise<Convoy>;
    /**
     * List all convoys
     *
     * @param status - Optional status filter
     * @returns Array of convoys
     */
    listConvoys(status?: ConvoyStatus): Convoy[];
    /**
     * Get convoy by ID
     *
     * @param convoyId - Convoy ID
     * @returns Convoy or undefined
     */
    getConvoy(convoyId: string): Convoy | undefined;
    /**
     * Delete a convoy
     *
     * @param convoyId - Convoy ID
     * @returns True if deleted
     */
    deleteConvoy(convoyId: string): boolean;
    /**
     * Calculate progress for a set of issues
     */
    private calculateProgress;
    /**
     * Verify issues exist
     */
    private verifyIssues;
    /**
     * Fetch beads by IDs
     */
    private fetchBeads;
    /**
     * Map CLI bead type to Gas Town status
     */
    private mapBeadStatus;
    /**
     * Start progress tracking timer
     */
    private startProgressTracking;
    /**
     * Stop progress tracking timer
     */
    private stopProgressTracking;
    /**
     * Emit convoy event
     */
    private emitConvoyEvent;
    /**
     * Clean up resources
     */
    dispose(): void;
}
/**
 * Create a new convoy tracker instance
 */
export declare function createConvoyTracker(config: ConvoyTrackerConfig, logger?: ConvoyLogger): ConvoyTracker;
export default ConvoyTracker;
//# sourceMappingURL=tracker.d.ts.map