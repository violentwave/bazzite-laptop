/**
 * GUPP State Persistence
 *
 * State management for the Gastown Universal Propulsion Principle (GUPP).
 * GUPP principle: "If work is on your hook, YOU MUST RUN IT"
 *
 * This module provides:
 * - State interfaces for tracking active work
 * - Disk/AgentDB persistence for crash recovery
 * - State merging for conflict resolution
 *
 * @module gastown-bridge/gupp/state
 * @version 0.1.0
 */
import { z } from 'zod';
import type { Convoy, Formula } from '../types.js';
/**
 * Default state file path
 */
export declare const DEFAULT_STATE_PATH = ".gupp/state.json";
/**
 * AgentDB namespace for GUPP state
 */
export declare const AGENTDB_NAMESPACE = "gupp:state";
/**
 * Work item status
 */
export type WorkItemStatus = 'pending' | 'active' | 'paused' | 'blocked' | 'completed' | 'failed';
/**
 * Work item on the hook
 */
export interface HookedWorkItem {
    /** Unique work item ID */
    readonly id: string;
    /** Associated bead ID (if any) */
    readonly beadId?: string;
    /** Associated convoy ID (if any) */
    readonly convoyId?: string;
    /** Work item title/description */
    readonly title: string;
    /** Current status */
    readonly status: WorkItemStatus;
    /** Priority (0 = highest) */
    readonly priority: number;
    /** When the work was hooked */
    readonly hookedAt: Date;
    /** When the work was last updated */
    readonly updatedAt: Date;
    /** Assigned agent */
    readonly assignee?: string;
    /** Formula applied to this work */
    readonly formula?: string;
    /** Progress percentage (0-100) */
    readonly progress: number;
    /** Error message if failed */
    readonly error?: string;
    /** Additional metadata */
    readonly metadata?: Record<string, unknown>;
}
/**
 * Session information
 */
export interface SessionInfo {
    /** Session ID */
    readonly id: string;
    /** When the session started */
    readonly startedAt: Date;
    /** When the session was last active */
    readonly lastActiveAt: Date;
    /** Whether the session is currently active */
    readonly active: boolean;
    /** Session owner/initiator */
    readonly owner?: string;
}
/**
 * GUPP State - Complete state for crash recovery
 */
export interface GuppState {
    /** State schema version */
    readonly version: number;
    /** Current session information */
    readonly session?: SessionInfo;
    /** Active convoys */
    readonly convoys: Convoy[];
    /** Active formulas (being executed) */
    readonly formulas: Array<{
        readonly name: string;
        readonly formula: Formula;
        readonly vars: Record<string, string>;
        readonly startedAt: Date;
        readonly status: 'cooking' | 'cooked' | 'executing' | 'completed' | 'failed';
    }>;
    /** Work items on the hook (GUPP principle) */
    readonly hookedWork: HookedWorkItem[];
    /** Last state update timestamp */
    readonly updatedAt: Date;
    /** State checksum for integrity verification */
    readonly checksum?: string;
    /** Recovery metadata */
    readonly recovery?: {
        readonly lastCrash?: Date;
        readonly crashCount: number;
        readonly autoRecoverEnabled: boolean;
    };
}
/**
 * Work item status schema
 */
declare const WorkItemStatusSchema: z.ZodEnum<["pending", "active", "paused", "blocked", "completed", "failed"]>;
/**
 * Hooked work item schema
 */
declare const HookedWorkItemSchema: z.ZodObject<{
    id: z.ZodString;
    beadId: z.ZodOptional<z.ZodString>;
    convoyId: z.ZodOptional<z.ZodString>;
    title: z.ZodString;
    status: z.ZodEnum<["pending", "active", "paused", "blocked", "completed", "failed"]>;
    priority: z.ZodNumber;
    hookedAt: z.ZodDate;
    updatedAt: z.ZodDate;
    assignee: z.ZodOptional<z.ZodString>;
    formula: z.ZodOptional<z.ZodString>;
    progress: z.ZodNumber;
    error: z.ZodOptional<z.ZodString>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    id: string;
    title: string;
    status: "active" | "failed" | "paused" | "blocked" | "pending" | "completed";
    priority: number;
    updatedAt: Date;
    progress: number;
    hookedAt: Date;
    beadId?: string | undefined;
    convoyId?: string | undefined;
    assignee?: string | undefined;
    metadata?: Record<string, unknown> | undefined;
    formula?: string | undefined;
    error?: string | undefined;
}, {
    id: string;
    title: string;
    status: "active" | "failed" | "paused" | "blocked" | "pending" | "completed";
    priority: number;
    updatedAt: Date;
    progress: number;
    hookedAt: Date;
    beadId?: string | undefined;
    convoyId?: string | undefined;
    assignee?: string | undefined;
    metadata?: Record<string, unknown> | undefined;
    formula?: string | undefined;
    error?: string | undefined;
}>;
/**
 * Session info schema
 */
declare const SessionInfoSchema: z.ZodObject<{
    id: z.ZodString;
    startedAt: z.ZodDate;
    lastActiveAt: z.ZodDate;
    active: z.ZodBoolean;
    owner: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    active: boolean;
    id: string;
    startedAt: Date;
    lastActiveAt: Date;
    owner?: string | undefined;
}, {
    active: boolean;
    id: string;
    startedAt: Date;
    lastActiveAt: Date;
    owner?: string | undefined;
}>;
/**
 * GUPP state schema
 */
declare const GuppStateSchema: z.ZodObject<{
    version: z.ZodNumber;
    session: z.ZodOptional<z.ZodObject<{
        id: z.ZodString;
        startedAt: z.ZodDate;
        lastActiveAt: z.ZodDate;
        active: z.ZodBoolean;
        owner: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        active: boolean;
        id: string;
        startedAt: Date;
        lastActiveAt: Date;
        owner?: string | undefined;
    }, {
        active: boolean;
        id: string;
        startedAt: Date;
        lastActiveAt: Date;
        owner?: string | undefined;
    }>>;
    convoys: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        trackedIssues: z.ZodArray<z.ZodString, "many">;
        status: z.ZodEnum<["active", "landed", "failed", "paused"]>;
        startedAt: z.ZodDate;
        completedAt: z.ZodOptional<z.ZodDate>;
        progress: z.ZodObject<{
            total: z.ZodNumber;
            closed: z.ZodNumber;
            inProgress: z.ZodNumber;
            blocked: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            closed: number;
            total: number;
            inProgress: number;
            blocked: number;
        }, {
            closed: number;
            total: number;
            inProgress: number;
            blocked: number;
        }>;
        formula: z.ZodOptional<z.ZodString>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        id: string;
        status: "active" | "landed" | "failed" | "paused";
        trackedIssues: string[];
        startedAt: Date;
        progress: {
            closed: number;
            total: number;
            inProgress: number;
            blocked: number;
        };
        description?: string | undefined;
        completedAt?: Date | undefined;
        formula?: string | undefined;
    }, {
        name: string;
        id: string;
        status: "active" | "landed" | "failed" | "paused";
        trackedIssues: string[];
        startedAt: Date;
        progress: {
            closed: number;
            total: number;
            inProgress: number;
            blocked: number;
        };
        description?: string | undefined;
        completedAt?: Date | undefined;
        formula?: string | undefined;
    }>, "many">;
    formulas: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        formula: z.ZodObject<{
            name: z.ZodString;
            description: z.ZodString;
            type: z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>;
            version: z.ZodNumber;
            legs: z.ZodOptional<z.ZodArray<z.ZodObject<{
                id: z.ZodString;
                title: z.ZodString;
                focus: z.ZodString;
                description: z.ZodString;
                agent: z.ZodOptional<z.ZodString>;
                order: z.ZodOptional<z.ZodNumber>;
            }, "strip", z.ZodTypeAny, {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }, {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }>, "many">>;
            steps: z.ZodOptional<z.ZodArray<z.ZodObject<{
                id: z.ZodString;
                title: z.ZodString;
                description: z.ZodString;
                needs: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
                duration: z.ZodOptional<z.ZodNumber>;
                requires: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
                metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
            }, "strip", z.ZodTypeAny, {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }, {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }>, "many">>;
            vars: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodObject<{
                name: z.ZodString;
                description: z.ZodOptional<z.ZodString>;
                default: z.ZodOptional<z.ZodString>;
                required: z.ZodOptional<z.ZodBoolean>;
                pattern: z.ZodOptional<z.ZodString>;
                enum: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
            }, "strip", z.ZodTypeAny, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }>>>;
        }, "strip", z.ZodTypeAny, {
            name: string;
            description: string;
            type: "convoy" | "workflow" | "expansion" | "aspect";
            version: number;
            legs?: {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }[] | undefined;
            steps?: {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }[] | undefined;
            vars?: Record<string, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }> | undefined;
        }, {
            name: string;
            description: string;
            type: "convoy" | "workflow" | "expansion" | "aspect";
            version: number;
            legs?: {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }[] | undefined;
            steps?: {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }[] | undefined;
            vars?: Record<string, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }> | undefined;
        }>;
        vars: z.ZodRecord<z.ZodString, z.ZodString>;
        startedAt: z.ZodDate;
        status: z.ZodEnum<["cooking", "cooked", "executing", "completed", "failed"]>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        status: "cooked" | "failed" | "completed" | "cooking" | "executing";
        vars: Record<string, string>;
        startedAt: Date;
        formula: {
            name: string;
            description: string;
            type: "convoy" | "workflow" | "expansion" | "aspect";
            version: number;
            legs?: {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }[] | undefined;
            steps?: {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }[] | undefined;
            vars?: Record<string, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }> | undefined;
        };
    }, {
        name: string;
        status: "cooked" | "failed" | "completed" | "cooking" | "executing";
        vars: Record<string, string>;
        startedAt: Date;
        formula: {
            name: string;
            description: string;
            type: "convoy" | "workflow" | "expansion" | "aspect";
            version: number;
            legs?: {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }[] | undefined;
            steps?: {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }[] | undefined;
            vars?: Record<string, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }> | undefined;
        };
    }>, "many">;
    hookedWork: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        beadId: z.ZodOptional<z.ZodString>;
        convoyId: z.ZodOptional<z.ZodString>;
        title: z.ZodString;
        status: z.ZodEnum<["pending", "active", "paused", "blocked", "completed", "failed"]>;
        priority: z.ZodNumber;
        hookedAt: z.ZodDate;
        updatedAt: z.ZodDate;
        assignee: z.ZodOptional<z.ZodString>;
        formula: z.ZodOptional<z.ZodString>;
        progress: z.ZodNumber;
        error: z.ZodOptional<z.ZodString>;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        title: string;
        status: "active" | "failed" | "paused" | "blocked" | "pending" | "completed";
        priority: number;
        updatedAt: Date;
        progress: number;
        hookedAt: Date;
        beadId?: string | undefined;
        convoyId?: string | undefined;
        assignee?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
        formula?: string | undefined;
        error?: string | undefined;
    }, {
        id: string;
        title: string;
        status: "active" | "failed" | "paused" | "blocked" | "pending" | "completed";
        priority: number;
        updatedAt: Date;
        progress: number;
        hookedAt: Date;
        beadId?: string | undefined;
        convoyId?: string | undefined;
        assignee?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
        formula?: string | undefined;
        error?: string | undefined;
    }>, "many">;
    updatedAt: z.ZodDate;
    checksum: z.ZodOptional<z.ZodString>;
    recovery: z.ZodOptional<z.ZodObject<{
        lastCrash: z.ZodOptional<z.ZodDate>;
        crashCount: z.ZodNumber;
        autoRecoverEnabled: z.ZodBoolean;
    }, "strip", z.ZodTypeAny, {
        crashCount: number;
        autoRecoverEnabled: boolean;
        lastCrash?: Date | undefined;
    }, {
        crashCount: number;
        autoRecoverEnabled: boolean;
        lastCrash?: Date | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    formulas: {
        name: string;
        status: "cooked" | "failed" | "completed" | "cooking" | "executing";
        vars: Record<string, string>;
        startedAt: Date;
        formula: {
            name: string;
            description: string;
            type: "convoy" | "workflow" | "expansion" | "aspect";
            version: number;
            legs?: {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }[] | undefined;
            steps?: {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }[] | undefined;
            vars?: Record<string, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }> | undefined;
        };
    }[];
    convoys: {
        name: string;
        id: string;
        status: "active" | "landed" | "failed" | "paused";
        trackedIssues: string[];
        startedAt: Date;
        progress: {
            closed: number;
            total: number;
            inProgress: number;
            blocked: number;
        };
        description?: string | undefined;
        completedAt?: Date | undefined;
        formula?: string | undefined;
    }[];
    updatedAt: Date;
    version: number;
    hookedWork: {
        id: string;
        title: string;
        status: "active" | "failed" | "paused" | "blocked" | "pending" | "completed";
        priority: number;
        updatedAt: Date;
        progress: number;
        hookedAt: Date;
        beadId?: string | undefined;
        convoyId?: string | undefined;
        assignee?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
        formula?: string | undefined;
        error?: string | undefined;
    }[];
    session?: {
        active: boolean;
        id: string;
        startedAt: Date;
        lastActiveAt: Date;
        owner?: string | undefined;
    } | undefined;
    checksum?: string | undefined;
    recovery?: {
        crashCount: number;
        autoRecoverEnabled: boolean;
        lastCrash?: Date | undefined;
    } | undefined;
}, {
    formulas: {
        name: string;
        status: "cooked" | "failed" | "completed" | "cooking" | "executing";
        vars: Record<string, string>;
        startedAt: Date;
        formula: {
            name: string;
            description: string;
            type: "convoy" | "workflow" | "expansion" | "aspect";
            version: number;
            legs?: {
                id: string;
                title: string;
                description: string;
                focus: string;
                agent?: string | undefined;
                order?: number | undefined;
            }[] | undefined;
            steps?: {
                id: string;
                title: string;
                description: string;
                needs?: string[] | undefined;
                duration?: number | undefined;
                requires?: string[] | undefined;
                metadata?: Record<string, unknown> | undefined;
            }[] | undefined;
            vars?: Record<string, {
                name: string;
                description?: string | undefined;
                default?: string | undefined;
                required?: boolean | undefined;
                pattern?: string | undefined;
                enum?: string[] | undefined;
            }> | undefined;
        };
    }[];
    convoys: {
        name: string;
        id: string;
        status: "active" | "landed" | "failed" | "paused";
        trackedIssues: string[];
        startedAt: Date;
        progress: {
            closed: number;
            total: number;
            inProgress: number;
            blocked: number;
        };
        description?: string | undefined;
        completedAt?: Date | undefined;
        formula?: string | undefined;
    }[];
    updatedAt: Date;
    version: number;
    hookedWork: {
        id: string;
        title: string;
        status: "active" | "failed" | "paused" | "blocked" | "pending" | "completed";
        priority: number;
        updatedAt: Date;
        progress: number;
        hookedAt: Date;
        beadId?: string | undefined;
        convoyId?: string | undefined;
        assignee?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
        formula?: string | undefined;
        error?: string | undefined;
    }[];
    session?: {
        active: boolean;
        id: string;
        startedAt: Date;
        lastActiveAt: Date;
        owner?: string | undefined;
    } | undefined;
    checksum?: string | undefined;
    recovery?: {
        crashCount: number;
        autoRecoverEnabled: boolean;
        lastCrash?: Date | undefined;
    } | undefined;
}>;
/**
 * Create an empty GUPP state
 */
export declare function createEmptyState(): GuppState;
/**
 * Create a new session
 */
export declare function createSession(id: string, owner?: string): SessionInfo;
/**
 * Create a hooked work item
 */
export declare function createHookedWorkItem(id: string, title: string, options?: Partial<Omit<HookedWorkItem, 'id' | 'title' | 'hookedAt' | 'updatedAt'>>): HookedWorkItem;
/**
 * Save state to disk
 *
 * @param state - State to save
 * @param statePath - Path to state file (default: .gupp/state.json)
 */
export declare function saveState(state: GuppState, statePath?: string): Promise<void>;
/**
 * Load state from disk
 *
 * @param statePath - Path to state file (default: .gupp/state.json)
 * @returns Loaded state or empty state if not found
 */
export declare function loadState(statePath?: string): Promise<GuppState>;
/**
 * Delete state file
 *
 * @param statePath - Path to state file
 */
export declare function deleteState(statePath?: string): Promise<void>;
/**
 * AgentDB interface for state storage
 */
export interface AgentDBInterface {
    store(namespace: string, key: string, value: unknown): Promise<void>;
    retrieve(namespace: string, key: string): Promise<unknown | null>;
    delete(namespace: string, key: string): Promise<void>;
}
/**
 * Save state to AgentDB
 *
 * @param state - State to save
 * @param agentDB - AgentDB interface
 * @param key - Storage key (default: 'current')
 */
export declare function saveStateToAgentDB(state: GuppState, agentDB: AgentDBInterface, key?: string): Promise<void>;
/**
 * Load state from AgentDB
 *
 * @param agentDB - AgentDB interface
 * @param key - Storage key (default: 'current')
 * @returns Loaded state or empty state if not found
 */
export declare function loadStateFromAgentDB(agentDB: AgentDBInterface, key?: string): Promise<GuppState>;
/**
 * Merge strategy for state conflicts
 */
export type MergeStrategy = 'local' | 'remote' | 'latest' | 'union';
/**
 * Merge two states on conflict
 *
 * Uses the following strategies:
 * - session: Keep the most recently active
 * - convoys: Union with latest status
 * - formulas: Union with latest status
 * - hookedWork: Union, prefer latest status for duplicates
 *
 * @param local - Local state
 * @param remote - Remote state
 * @param strategy - Merge strategy (default: 'latest')
 * @returns Merged state
 */
export declare function mergeStates(local: GuppState, remote: GuppState, strategy?: MergeStrategy): GuppState;
/**
 * Validate state structure
 */
export declare function validateState(state: unknown): state is GuppState;
/**
 * Get pending work items (GUPP principle: must run these)
 */
export declare function getPendingWork(state: GuppState): HookedWorkItem[];
/**
 * Get work items that need resumption after crash
 */
export declare function getWorkNeedingResumption(state: GuppState): HookedWorkItem[];
/**
 * Update session activity timestamp
 */
export declare function touchSession(state: GuppState): GuppState;
/**
 * Mark session as ended
 */
export declare function endSession(state: GuppState): GuppState;
export { GuppStateSchema, HookedWorkItemSchema, SessionInfoSchema, WorkItemStatusSchema, };
//# sourceMappingURL=state.d.ts.map