/**
 * Gas Town Bridge Plugin - Type Definitions
 *
 * Core types for Gas Town integration including:
 * - Beads: Git-backed issue tracking with graph semantics
 * - Formulas: TOML-defined workflows (convoy, workflow, expansion, aspect)
 * - Convoys: Work-order tracking for slung work
 * - Steps/Legs: Workflow components
 * - Variables: Template substitution
 *
 * @module gastown-bridge/types
 * @version 0.1.0
 */
import { z } from 'zod';
/**
 * Bead status enumeration
 */
export type BeadStatus = 'open' | 'in_progress' | 'closed';
/**
 * Bead - Git-backed issue with graph semantics
 */
export interface Bead {
    /** Unique identifier (e.g., "gt-abc12") */
    readonly id: string;
    /** Issue title */
    readonly title: string;
    /** Issue description */
    readonly description: string;
    /** Current status */
    readonly status: BeadStatus;
    /** Priority (0 = highest) */
    readonly priority: number;
    /** Issue labels */
    readonly labels: string[];
    /** Parent bead ID (for epics) */
    readonly parentId?: string;
    /** Creation timestamp */
    readonly createdAt: Date;
    /** Last update timestamp */
    readonly updatedAt: Date;
    /** Assigned agent/user */
    readonly assignee?: string;
    /** Gas Town rig name */
    readonly rig?: string;
    /** Blocking beads (dependencies) */
    readonly blockedBy?: string[];
    /** Beads this blocks */
    readonly blocks?: string[];
}
/**
 * Options for creating a new bead
 */
export interface CreateBeadOptions {
    readonly title: string;
    readonly description?: string;
    readonly priority?: number;
    readonly labels?: string[];
    readonly parent?: string;
    readonly rig?: string;
    readonly assignee?: string;
}
/**
 * Bead dependency relationship
 */
export interface BeadDependency {
    readonly child: string;
    readonly parent: string;
    readonly type: 'blocks' | 'relates' | 'duplicates';
}
/**
 * Formula type enumeration
 */
export type FormulaType = 'convoy' | 'workflow' | 'expansion' | 'aspect';
/**
 * Workflow step definition
 */
export interface Step {
    /** Step identifier */
    readonly id: string;
    /** Step title */
    readonly title: string;
    /** Step description */
    readonly description: string;
    /** Dependencies - step IDs that must complete first */
    readonly needs?: string[];
    /** Estimated duration in minutes */
    readonly duration?: number;
    /** Required capabilities */
    readonly requires?: string[];
    /** Step metadata */
    readonly metadata?: Record<string, unknown>;
}
/**
 * Convoy leg definition
 */
export interface Leg {
    /** Leg identifier */
    readonly id: string;
    /** Leg title */
    readonly title: string;
    /** Focus area */
    readonly focus: string;
    /** Leg description */
    readonly description: string;
    /** Assigned agent type */
    readonly agent?: string;
    /** Leg sequence order */
    readonly order?: number;
}
/**
 * Formula variable definition
 */
export interface Var {
    /** Variable name */
    readonly name: string;
    /** Variable description */
    readonly description?: string;
    /** Default value */
    readonly default?: string;
    /** Whether the variable is required */
    readonly required?: boolean;
    /** Validation pattern (regex) */
    readonly pattern?: string;
    /** Allowed values */
    readonly enum?: string[];
}
/**
 * Synthesis definition (convoy result combination)
 */
export interface Synthesis {
    /** Synthesis strategy */
    readonly strategy: 'merge' | 'sequential' | 'parallel';
    /** Output format */
    readonly format?: string;
    /** Synthesis description */
    readonly description?: string;
}
/**
 * Template for expansion formulas
 */
export interface Template {
    /** Template name */
    readonly name: string;
    /** Template content with variable placeholders */
    readonly content: string;
    /** Output path pattern */
    readonly outputPath?: string;
}
/**
 * Aspect definition for cross-cutting concerns
 */
export interface Aspect {
    /** Aspect name */
    readonly name: string;
    /** Pointcut expression */
    readonly pointcut: string;
    /** Advice to apply */
    readonly advice: string;
    /** Aspect type */
    readonly type: 'before' | 'after' | 'around';
}
/**
 * Formula - TOML-defined workflow specification
 */
export interface Formula {
    /** Formula name */
    readonly name: string;
    /** Formula description */
    readonly description: string;
    /** Formula type */
    readonly type: FormulaType;
    /** Formula version */
    readonly version: number;
    /** Convoy legs */
    readonly legs?: Leg[];
    /** Synthesis configuration */
    readonly synthesis?: Synthesis;
    /** Workflow steps */
    readonly steps?: Step[];
    /** Variable definitions */
    readonly vars?: Record<string, Var>;
    /** Expansion templates */
    readonly templates?: Template[];
    /** Cross-cutting aspects */
    readonly aspects?: Aspect[];
    /** Formula metadata */
    readonly metadata?: Record<string, unknown>;
}
/**
 * Cooked formula with variables substituted
 */
export interface CookedFormula extends Formula {
    /** When the formula was cooked */
    readonly cookedAt: Date;
    /** Variables used for cooking */
    readonly cookedVars: Record<string, string>;
    /** Original (uncooked) formula name */
    readonly originalName: string;
}
/**
 * Convoy status enumeration
 */
export type ConvoyStatus = 'active' | 'landed' | 'failed' | 'paused';
/**
 * Convoy progress tracking
 */
export interface ConvoyProgress {
    /** Total issues tracked */
    readonly total: number;
    /** Closed issues */
    readonly closed: number;
    /** In-progress issues */
    readonly inProgress: number;
    /** Blocked issues */
    readonly blocked: number;
}
/**
 * Convoy - Work order tracking for slung work
 */
export interface Convoy {
    /** Convoy identifier */
    readonly id: string;
    /** Convoy name */
    readonly name: string;
    /** Tracked issue IDs */
    readonly trackedIssues: string[];
    /** Convoy status */
    readonly status: ConvoyStatus;
    /** Start timestamp */
    readonly startedAt: Date;
    /** Completion timestamp */
    readonly completedAt?: Date;
    /** Progress tracking */
    readonly progress: ConvoyProgress;
    /** Formula used to create convoy */
    readonly formula?: string;
    /** Description */
    readonly description?: string;
}
/**
 * Options for creating a convoy
 */
export interface CreateConvoyOptions {
    readonly name: string;
    readonly issues: string[];
    readonly description?: string;
    readonly formula?: string;
}
/**
 * Gas Town agent role
 */
export type GasTownAgentRole = 'mayor' | 'polecat' | 'refinery' | 'witness' | 'deacon' | 'dog' | 'crew';
/**
 * Gas Town agent
 */
export interface GasTownAgent {
    /** Agent name */
    readonly name: string;
    /** Agent role */
    readonly role: GasTownAgentRole;
    /** Rig assignment */
    readonly rig?: string;
    /** Current status */
    readonly status: 'active' | 'idle' | 'busy';
    /** Agent capabilities */
    readonly capabilities?: string[];
}
/**
 * Sling target type
 */
export type SlingTarget = 'polecat' | 'crew' | 'mayor';
/**
 * Sling operation options
 */
export interface SlingOptions {
    readonly beadId: string;
    readonly target: SlingTarget;
    readonly formula?: string;
    readonly priority?: number;
}
/**
 * Gas Town mail message
 */
export interface GasTownMail {
    readonly id: string;
    readonly from: string;
    readonly to: string;
    readonly subject: string;
    readonly body: string;
    readonly sentAt: Date;
    readonly read: boolean;
}
/**
 * Sync direction
 */
export type SyncDirection = 'pull' | 'push' | 'both';
/**
 * Sync result
 */
export interface SyncResult {
    readonly direction: SyncDirection;
    readonly pulled: number;
    readonly pushed: number;
    readonly errors: string[];
    readonly timestamp: Date;
}
/**
 * Dependency graph for beads
 */
export interface BeadGraph {
    readonly nodes: string[];
    readonly edges: Array<[string, string]>;
}
/**
 * Topological sort result
 */
export interface TopoSortResult {
    readonly sorted: string[];
    readonly hasCycle: boolean;
    readonly cycleNodes?: string[];
}
/**
 * Critical path result
 */
export interface CriticalPathResult {
    readonly path: string[];
    readonly totalDuration: number;
    readonly slack: Map<string, number>;
}
/**
 * Gas Town Bridge plugin configuration
 */
export interface GasTownConfig {
    /** Path to Gas Town installation */
    readonly townRoot: string;
    /** Enable Beads sync with AgentDB */
    readonly enableBeadsSync: boolean;
    /** Sync interval in milliseconds */
    readonly syncInterval: number;
    /** Enable native formula parsing (WASM) */
    readonly nativeFormulas: boolean;
    /** Enable convoy tracking */
    readonly enableConvoys: boolean;
    /** Auto-create beads from Claude Flow tasks */
    readonly autoCreateBeads: boolean;
    /** Enable GUPP integration */
    readonly enableGUPP: boolean;
    /** GUPP check interval in milliseconds */
    readonly guppCheckInterval: number;
    /** CLI timeout in milliseconds */
    readonly cliTimeout: number;
}
/**
 * Default configuration values
 */
export declare const DEFAULT_CONFIG: GasTownConfig;
/**
 * Gas Town Bridge error codes
 */
export declare const GasTownErrorCodes: {
    readonly CLI_NOT_FOUND: "GT_CLI_NOT_FOUND";
    readonly CLI_TIMEOUT: "GT_CLI_TIMEOUT";
    readonly CLI_ERROR: "GT_CLI_ERROR";
    readonly BEAD_NOT_FOUND: "GT_BEAD_NOT_FOUND";
    readonly CONVOY_NOT_FOUND: "GT_CONVOY_NOT_FOUND";
    readonly FORMULA_NOT_FOUND: "GT_FORMULA_NOT_FOUND";
    readonly FORMULA_PARSE_ERROR: "GT_FORMULA_PARSE_ERROR";
    readonly WASM_NOT_INITIALIZED: "GT_WASM_NOT_INITIALIZED";
    readonly SYNC_ERROR: "GT_SYNC_ERROR";
    readonly DEPENDENCY_CYCLE: "GT_DEPENDENCY_CYCLE";
    readonly INVALID_SLING_TARGET: "GT_INVALID_SLING_TARGET";
};
export type GasTownErrorCode = (typeof GasTownErrorCodes)[keyof typeof GasTownErrorCodes];
/**
 * Bead status schema
 */
export declare const BeadStatusSchema: z.ZodEnum<["open", "in_progress", "closed"]>;
/**
 * Bead schema
 */
export declare const BeadSchema: z.ZodObject<{
    id: z.ZodString;
    title: z.ZodString;
    description: z.ZodString;
    status: z.ZodEnum<["open", "in_progress", "closed"]>;
    priority: z.ZodNumber;
    labels: z.ZodArray<z.ZodString, "many">;
    parentId: z.ZodOptional<z.ZodString>;
    createdAt: z.ZodDate;
    updatedAt: z.ZodDate;
    assignee: z.ZodOptional<z.ZodString>;
    rig: z.ZodOptional<z.ZodString>;
    blockedBy: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocks: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    id: string;
    title: string;
    description: string;
    status: "open" | "in_progress" | "closed";
    priority: number;
    labels: string[];
    createdAt: Date;
    updatedAt: Date;
    blocks?: string[] | undefined;
    parentId?: string | undefined;
    assignee?: string | undefined;
    rig?: string | undefined;
    blockedBy?: string[] | undefined;
}, {
    id: string;
    title: string;
    description: string;
    status: "open" | "in_progress" | "closed";
    priority: number;
    labels: string[];
    createdAt: Date;
    updatedAt: Date;
    blocks?: string[] | undefined;
    parentId?: string | undefined;
    assignee?: string | undefined;
    rig?: string | undefined;
    blockedBy?: string[] | undefined;
}>;
/**
 * Create bead options schema
 */
export declare const CreateBeadOptionsSchema: z.ZodObject<{
    title: z.ZodString;
    description: z.ZodOptional<z.ZodString>;
    priority: z.ZodOptional<z.ZodNumber>;
    labels: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    parent: z.ZodOptional<z.ZodString>;
    rig: z.ZodOptional<z.ZodString>;
    assignee: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    title: string;
    description?: string | undefined;
    priority?: number | undefined;
    labels?: string[] | undefined;
    assignee?: string | undefined;
    rig?: string | undefined;
    parent?: string | undefined;
}, {
    title: string;
    description?: string | undefined;
    priority?: number | undefined;
    labels?: string[] | undefined;
    assignee?: string | undefined;
    rig?: string | undefined;
    parent?: string | undefined;
}>;
/**
 * Formula type schema
 */
export declare const FormulaTypeSchema: z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>;
/**
 * Step schema
 */
export declare const StepSchema: z.ZodObject<{
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
}>;
/**
 * Leg schema
 */
export declare const LegSchema: z.ZodObject<{
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
}>;
/**
 * Variable schema
 */
export declare const VarSchema: z.ZodObject<{
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
}>;
/**
 * Synthesis schema
 */
export declare const SynthesisSchema: z.ZodObject<{
    strategy: z.ZodEnum<["merge", "sequential", "parallel"]>;
    format: z.ZodOptional<z.ZodString>;
    description: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    strategy: "merge" | "sequential" | "parallel";
    description?: string | undefined;
    format?: string | undefined;
}, {
    strategy: "merge" | "sequential" | "parallel";
    description?: string | undefined;
    format?: string | undefined;
}>;
/**
 * Template schema
 */
export declare const TemplateSchema: z.ZodObject<{
    name: z.ZodString;
    content: z.ZodString;
    outputPath: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    content: string;
    outputPath?: string | undefined;
}, {
    name: string;
    content: string;
    outputPath?: string | undefined;
}>;
/**
 * Aspect schema
 */
export declare const AspectSchema: z.ZodObject<{
    name: z.ZodString;
    pointcut: z.ZodString;
    advice: z.ZodString;
    type: z.ZodEnum<["before", "after", "around"]>;
}, "strip", z.ZodTypeAny, {
    name: string;
    type: "before" | "after" | "around";
    pointcut: string;
    advice: string;
}, {
    name: string;
    type: "before" | "after" | "around";
    pointcut: string;
    advice: string;
}>;
/**
 * Formula schema
 */
export declare const FormulaSchema: z.ZodObject<{
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
    synthesis: z.ZodOptional<z.ZodObject<{
        strategy: z.ZodEnum<["merge", "sequential", "parallel"]>;
        format: z.ZodOptional<z.ZodString>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    }, {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    }>>;
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
    templates: z.ZodOptional<z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        content: z.ZodString;
        outputPath: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        content: string;
        outputPath?: string | undefined;
    }, {
        name: string;
        content: string;
        outputPath?: string | undefined;
    }>, "many">>;
    aspects: z.ZodOptional<z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        pointcut: z.ZodString;
        advice: z.ZodString;
        type: z.ZodEnum<["before", "after", "around"]>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }, {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }>, "many">>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    name: string;
    description: string;
    type: "convoy" | "workflow" | "expansion" | "aspect";
    version: number;
    metadata?: Record<string, unknown> | undefined;
    legs?: {
        id: string;
        title: string;
        description: string;
        focus: string;
        agent?: string | undefined;
        order?: number | undefined;
    }[] | undefined;
    synthesis?: {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    } | undefined;
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
    templates?: {
        name: string;
        content: string;
        outputPath?: string | undefined;
    }[] | undefined;
    aspects?: {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }[] | undefined;
}, {
    name: string;
    description: string;
    type: "convoy" | "workflow" | "expansion" | "aspect";
    version: number;
    metadata?: Record<string, unknown> | undefined;
    legs?: {
        id: string;
        title: string;
        description: string;
        focus: string;
        agent?: string | undefined;
        order?: number | undefined;
    }[] | undefined;
    synthesis?: {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    } | undefined;
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
    templates?: {
        name: string;
        content: string;
        outputPath?: string | undefined;
    }[] | undefined;
    aspects?: {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }[] | undefined;
}>;
/**
 * Convoy status schema
 */
export declare const ConvoyStatusSchema: z.ZodEnum<["active", "landed", "failed", "paused"]>;
/**
 * Convoy progress schema
 */
export declare const ConvoyProgressSchema: z.ZodObject<{
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
/**
 * Convoy schema
 */
export declare const ConvoySchema: z.ZodObject<{
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
}>;
/**
 * Create convoy options schema
 */
export declare const CreateConvoyOptionsSchema: z.ZodObject<{
    name: z.ZodString;
    issues: z.ZodArray<z.ZodString, "many">;
    description: z.ZodOptional<z.ZodString>;
    formula: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    issues: string[];
    description?: string | undefined;
    formula?: string | undefined;
}, {
    name: string;
    issues: string[];
    description?: string | undefined;
    formula?: string | undefined;
}>;
/**
 * Gas Town agent role schema
 */
export declare const GasTownAgentRoleSchema: z.ZodEnum<["mayor", "polecat", "refinery", "witness", "deacon", "dog", "crew"]>;
/**
 * Sling target schema
 */
export declare const SlingTargetSchema: z.ZodEnum<["polecat", "crew", "mayor"]>;
/**
 * Sling options schema
 */
export declare const SlingOptionsSchema: z.ZodObject<{
    beadId: z.ZodString;
    target: z.ZodEnum<["polecat", "crew", "mayor"]>;
    formula: z.ZodOptional<z.ZodString>;
    priority: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    beadId: string;
    target: "mayor" | "polecat" | "crew";
    priority?: number | undefined;
    formula?: string | undefined;
}, {
    beadId: string;
    target: "mayor" | "polecat" | "crew";
    priority?: number | undefined;
    formula?: string | undefined;
}>;
/**
 * Sync direction schema
 */
export declare const SyncDirectionSchema: z.ZodEnum<["pull", "push", "both"]>;
/**
 * Configuration schema
 */
export declare const GasTownConfigSchema: z.ZodObject<{
    townRoot: z.ZodDefault<z.ZodString>;
    enableBeadsSync: z.ZodDefault<z.ZodBoolean>;
    syncInterval: z.ZodDefault<z.ZodNumber>;
    nativeFormulas: z.ZodDefault<z.ZodBoolean>;
    enableConvoys: z.ZodDefault<z.ZodBoolean>;
    autoCreateBeads: z.ZodDefault<z.ZodBoolean>;
    enableGUPP: z.ZodDefault<z.ZodBoolean>;
    guppCheckInterval: z.ZodDefault<z.ZodNumber>;
    cliTimeout: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    townRoot: string;
    enableBeadsSync: boolean;
    syncInterval: number;
    nativeFormulas: boolean;
    enableConvoys: boolean;
    autoCreateBeads: boolean;
    enableGUPP: boolean;
    guppCheckInterval: number;
    cliTimeout: number;
}, {
    townRoot?: string | undefined;
    enableBeadsSync?: boolean | undefined;
    syncInterval?: number | undefined;
    nativeFormulas?: boolean | undefined;
    enableConvoys?: boolean | undefined;
    autoCreateBeads?: boolean | undefined;
    enableGUPP?: boolean | undefined;
    guppCheckInterval?: number | undefined;
    cliTimeout?: number | undefined;
}>;
/**
 * Validate bead
 */
export declare function validateBead(input: unknown): Bead;
/**
 * Validate create bead options
 */
export declare function validateCreateBeadOptions(input: unknown): CreateBeadOptions;
/**
 * Validate formula
 */
export declare function validateFormula(input: unknown): Formula;
/**
 * Validate convoy
 */
export declare function validateConvoy(input: unknown): Convoy;
/**
 * Validate create convoy options
 */
export declare function validateCreateConvoyOptions(input: unknown): CreateConvoyOptions;
/**
 * Validate sling options
 */
export declare function validateSlingOptions(input: unknown): SlingOptions;
/**
 * Validate configuration
 */
export declare function validateConfig(input: unknown): GasTownConfig;
/**
 * Dependency action type
 */
export type DepAction = 'add' | 'remove';
/**
 * Convoy action type
 */
export type ConvoyAction = 'create' | 'track' | 'land' | 'pause' | 'resume';
/**
 * Mail action type
 */
export type MailAction = 'send' | 'read' | 'list';
/**
 * Agent role type (alias for GasTownAgentRole)
 */
export type AgentRole = GasTownAgentRole;
/**
 * Target agent type (alias for SlingTarget)
 */
export type TargetAgent = SlingTarget;
/**
 * Convoy strategy type
 */
export type ConvoyStrategy = 'parallel' | 'serial' | 'hybrid' | 'fastest' | 'balanced' | 'throughput' | 'minimal_context_switches';
/**
 * Dependency action type (for graph operations)
 */
export type DependencyAction = 'topo_sort' | 'cycle_detect' | 'critical_path';
/**
 * Formula AST (Abstract Syntax Tree) - alias for Formula
 */
export type FormulaAST = Formula;
/**
 * Dependency resolution result
 */
export interface DependencyResolution {
    readonly action: DependencyAction;
    readonly sorted?: string[];
    readonly hasCycle?: boolean;
    readonly cycleNodes?: string[];
    readonly criticalPath?: string[];
    readonly totalDuration?: number;
}
/**
 * Pattern match result
 */
export interface PatternMatch {
    readonly index: number;
    readonly candidate: string;
    readonly similarity: number;
}
/**
 * Convoy optimization result
 */
export interface ConvoyOptimization {
    readonly convoyId: string;
    readonly strategy: string;
    readonly executionOrder: string[];
    readonly parallelGroups: string[][];
    readonly estimatedDuration: number;
}
/**
 * Gas Town Bridge interface
 */
export interface IGasTownBridge {
    createBead(opts: CreateBeadOptions): Promise<Bead>;
    getReady(limit?: number, rig?: string, labels?: string[]): Promise<Bead[]>;
    showBead(beadId: string): Promise<{
        bead: Bead;
        dependencies: string[];
        dependents: string[];
    }>;
    manageDependency(action: DepAction, child: string, parent: string): Promise<void>;
    createConvoy(opts: CreateConvoyOptions): Promise<Convoy>;
    getConvoyStatus(convoyId?: string, detailed?: boolean): Promise<Convoy[]>;
    trackConvoy(convoyId: string, action: 'add' | 'remove', issues: string[]): Promise<void>;
    listFormulas(type?: FormulaType, includeBuiltin?: boolean): Promise<Array<{
        name: string;
        type: FormulaType;
        description: string;
        builtin: boolean;
    }>>;
    cookFormula(formula: Formula | string, vars: Record<string, string>): Promise<CookedFormula>;
    executeFormula(formula: Formula | string, vars: Record<string, string>, targetAgent?: string, dryRun?: boolean): Promise<{
        beads_created: string[];
    }>;
    createFormula(opts: {
        name: string;
        type: FormulaType;
        steps?: Step[];
        vars?: Record<string, unknown>;
        description?: string;
    }): Promise<{
        path: string;
    }>;
    sling(beadId: string, target: SlingTarget, formula?: string, priority?: number): Promise<void>;
    listAgents(rig?: string, role?: AgentRole, includeInactive?: boolean): Promise<GasTownAgent[]>;
    sendMail(to: string, subject: string, body: string): Promise<string>;
    readMail(mailId: string): Promise<GasTownMail>;
    listMail(limit?: number): Promise<GasTownMail[]>;
}
/**
 * Beads sync service interface
 */
export interface IBeadsSyncService {
    pullBeads(rig?: string, namespace?: string): Promise<{
        synced: number;
        conflicts: number;
    }>;
    pushTasks(namespace?: string): Promise<{
        pushed: number;
        conflicts: number;
    }>;
}
/**
 * Formula WASM interface
 */
export interface IFormulaWasm {
    isInitialized(): boolean;
    initialize(): Promise<void>;
    parseFormula(content: string, validate?: boolean): Promise<Formula>;
    cookFormula(formula: Formula | string, vars: Record<string, string>, isContent?: boolean): Promise<CookedFormula>;
    cookBatch(formulas: Array<{
        name: string;
        content: string;
    }>, vars: Record<string, string>[], continueOnError?: boolean): Promise<{
        cooked: CookedFormula[];
        errors: Array<{
            index: number;
            error: string;
        }>;
    }>;
}
/**
 * Dependency WASM interface
 */
export interface IDependencyWasm {
    isInitialized(): boolean;
    initialize(): Promise<void>;
    resolveDependencies(beads: Array<{
        id: string;
        dependencies?: string[];
    }>, action: DependencyAction): Promise<DependencyResolution>;
    matchPatterns(query: string, candidates: string[], k: number, threshold: number): Promise<PatternMatch[]>;
    optimizeConvoy(convoy: {
        id: string;
        trackedIssues: string[];
    }, strategy: ConvoyStrategy, constraints?: unknown): Promise<ConvoyOptimization>;
}
//# sourceMappingURL=types.d.ts.map