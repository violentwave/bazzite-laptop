/**
 * Gas Town Bridge Plugin - MCP Tools
 *
 * Implements 20 MCP tools for Gas Town orchestrator integration:
 *
 * Beads Integration (5 tools) - CLI Bridge:
 *   1. gt_beads_create - Create a bead/issue in Beads
 *   2. gt_beads_ready - List ready beads (no blockers)
 *   3. gt_beads_show - Show bead details
 *   4. gt_beads_dep - Manage bead dependencies
 *   5. gt_beads_sync - Sync beads with AgentDB
 *
 * Convoy Operations (3 tools) - CLI Bridge:
 *   6. gt_convoy_create - Create a convoy (work order)
 *   7. gt_convoy_status - Check convoy status
 *   8. gt_convoy_track - Add/remove issues from convoy
 *
 * Formula Engine (4 tools) - WASM Accelerated:
 *   9. gt_formula_list - List available formulas
 *   10. gt_formula_cook - Cook formula into protomolecule (352x faster)
 *   11. gt_formula_execute - Execute a formula
 *   12. gt_formula_create - Create custom formula
 *
 * Orchestration (3 tools) - CLI Bridge:
 *   13. gt_sling - Sling work to an agent
 *   14. gt_agents - List Gas Town agents
 *   15. gt_mail - Send/receive Gas Town mail
 *
 * WASM Computation (5 tools) - Pure WASM:
 *   16. gt_wasm_parse_formula - Parse TOML formula to AST
 *   17. gt_wasm_resolve_deps - Resolve dependency graph
 *   18. gt_wasm_cook_batch - Batch cook multiple formulas
 *   19. gt_wasm_match_pattern - Find similar formulas/beads
 *   20. gt_wasm_optimize_convoy - Optimize convoy execution order
 *
 * Based on ADR-043: Gas Town Bridge Plugin for Claude Flow V3
 *
 * @module v3/plugins/gastown-bridge/mcp-tools
 */
import { z } from 'zod';
import type { Bead, Convoy, FormulaType, CookedFormula, GasTownAgent, GasTownMail, DepAction, SyncDirection, MailAction, TargetAgent, DependencyAction, FormulaAST, DependencyResolution, PatternMatch, ConvoyOptimization, IGasTownBridge, IBeadsSyncService, IFormulaWasm, IDependencyWasm } from './types.js';
/**
 * MCP Tool definition
 */
export interface MCPTool<TInput = unknown, TOutput = unknown> {
    /** Tool name (e.g., "gt_beads_create") */
    name: string;
    /** Tool description */
    description: string;
    /** Tool category */
    category: string;
    /** Tool version */
    version: string;
    /** Execution layer (cli, wasm, hybrid) */
    layer: 'cli' | 'wasm' | 'hybrid';
    /** Input schema */
    inputSchema: z.ZodType<TInput, z.ZodTypeDef, unknown>;
    /** Handler function */
    handler: (input: TInput, context: ToolContext) => Promise<MCPToolResult<TOutput>>;
}
/**
 * Tool execution context
 */
export interface ToolContext {
    /** Key-value store for cross-tool state */
    get<T>(key: string): T | undefined;
    set<T>(key: string, value: T): void;
    /** Bridge instances */
    bridges: {
        gastown: IGasTownBridge;
        beadsSync: IBeadsSyncService;
        formulaWasm: IFormulaWasm;
        dependencyWasm: IDependencyWasm;
    };
    /** Configuration */
    config: {
        townRoot: string;
        allowedRigs: string[];
        maxBeadsLimit: number;
        maskSecrets: boolean;
        enableWasm: boolean;
    };
}
/**
 * MCP Tool result format
 */
export interface MCPToolResult<T = unknown> {
    content: Array<{
        type: 'text';
        text: string;
    }>;
    data?: T;
}
/**
 * Schema for gt_beads_create
 */
export declare const BeadsCreateInputSchema: z.ZodObject<{
    /** Bead title */
    title: z.ZodString;
    /** Bead description */
    description: z.ZodOptional<z.ZodString>;
    /** Priority (0 = highest) */
    priority: z.ZodDefault<z.ZodNumber>;
    /** Labels for categorization */
    labels: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    /** Parent bead ID for epics */
    parent: z.ZodOptional<z.ZodString>;
    /** Rig (repository) to create in */
    rig: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    title: string;
    priority: number;
    description?: string | undefined;
    labels?: string[] | undefined;
    rig?: string | undefined;
    parent?: string | undefined;
}, {
    title: string;
    description?: string | undefined;
    priority?: number | undefined;
    labels?: string[] | undefined;
    rig?: string | undefined;
    parent?: string | undefined;
}>;
export type BeadsCreateInput = z.infer<typeof BeadsCreateInputSchema>;
/**
 * Schema for gt_beads_ready
 */
export declare const BeadsReadyInputSchema: z.ZodObject<{
    /** Filter by rig */
    rig: z.ZodOptional<z.ZodString>;
    /** Maximum beads to return */
    limit: z.ZodDefault<z.ZodNumber>;
    /** Filter by labels */
    labels: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    limit: number;
    labels?: string[] | undefined;
    rig?: string | undefined;
}, {
    labels?: string[] | undefined;
    rig?: string | undefined;
    limit?: number | undefined;
}>;
export type BeadsReadyInput = z.infer<typeof BeadsReadyInputSchema>;
/**
 * Schema for gt_beads_show
 */
export declare const BeadsShowInputSchema: z.ZodObject<{
    /** Bead ID to show */
    bead_id: z.ZodString;
}, "strip", z.ZodTypeAny, {
    bead_id: string;
}, {
    bead_id: string;
}>;
export type BeadsShowInput = z.infer<typeof BeadsShowInputSchema>;
/**
 * Schema for gt_beads_dep
 */
export declare const BeadsDepInputSchema: z.ZodObject<{
    /** Action to perform */
    action: z.ZodEnum<["add", "remove"]>;
    /** Child bead ID (the one that depends) */
    child: z.ZodString;
    /** Parent bead ID (the dependency) */
    parent: z.ZodString;
}, "strip", z.ZodTypeAny, {
    parent: string;
    action: "add" | "remove";
    child: string;
}, {
    parent: string;
    action: "add" | "remove";
    child: string;
}>;
export type BeadsDepInput = z.infer<typeof BeadsDepInputSchema>;
/**
 * Schema for gt_beads_sync
 */
export declare const BeadsSyncInputSchema: z.ZodObject<{
    /** Sync direction */
    direction: z.ZodDefault<z.ZodEnum<["pull", "push", "both"]>>;
    /** Filter by rig */
    rig: z.ZodOptional<z.ZodString>;
    /** AgentDB namespace for sync */
    namespace: z.ZodDefault<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    namespace: string;
    direction: "push" | "pull" | "both";
    rig?: string | undefined;
}, {
    rig?: string | undefined;
    namespace?: string | undefined;
    direction?: "push" | "pull" | "both" | undefined;
}>;
export type BeadsSyncInput = z.infer<typeof BeadsSyncInputSchema>;
/**
 * Schema for gt_convoy_create
 */
export declare const ConvoyCreateInputSchema: z.ZodObject<{
    /** Convoy name */
    name: z.ZodString;
    /** Issue IDs to track */
    issues: z.ZodArray<z.ZodString, "many">;
    /** Convoy description */
    description: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    issues: string[];
    description?: string | undefined;
}, {
    name: string;
    issues: string[];
    description?: string | undefined;
}>;
export type ConvoyCreateInput = z.infer<typeof ConvoyCreateInputSchema>;
/**
 * Schema for gt_convoy_status
 */
export declare const ConvoyStatusInputSchema: z.ZodObject<{
    /** Convoy ID (optional - shows all if omitted) */
    convoy_id: z.ZodOptional<z.ZodString>;
    /** Include detailed progress */
    detailed: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    detailed: boolean;
    convoy_id?: string | undefined;
}, {
    convoy_id?: string | undefined;
    detailed?: boolean | undefined;
}>;
export type ConvoyStatusInput = z.infer<typeof ConvoyStatusInputSchema>;
/**
 * Schema for gt_convoy_track
 */
export declare const ConvoyTrackInputSchema: z.ZodObject<{
    /** Convoy ID */
    convoy_id: z.ZodString;
    /** Action to perform */
    action: z.ZodEnum<["add", "remove"]>;
    /** Issue IDs to add/remove */
    issues: z.ZodArray<z.ZodString, "many">;
}, "strip", z.ZodTypeAny, {
    issues: string[];
    action: "add" | "remove";
    convoy_id: string;
}, {
    issues: string[];
    action: "add" | "remove";
    convoy_id: string;
}>;
export type ConvoyTrackInput = z.infer<typeof ConvoyTrackInputSchema>;
/**
 * Schema for gt_formula_list
 */
export declare const FormulaListInputSchema: z.ZodObject<{
    /** Filter by formula type */
    type: z.ZodOptional<z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>>;
    /** Include built-in formulas */
    include_builtin: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    include_builtin: boolean;
    type?: "convoy" | "workflow" | "expansion" | "aspect" | undefined;
}, {
    type?: "convoy" | "workflow" | "expansion" | "aspect" | undefined;
    include_builtin?: boolean | undefined;
}>;
export type FormulaListInput = z.infer<typeof FormulaListInputSchema>;
/**
 * Schema for gt_formula_cook
 */
export declare const FormulaCookInputSchema: z.ZodObject<{
    /** Formula name or TOML content */
    formula: z.ZodString;
    /** Variables for substitution */
    vars: z.ZodRecord<z.ZodString, z.ZodString>;
    /** Whether formula is TOML content (vs name) */
    is_content: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    vars: Record<string, string>;
    formula: string;
    is_content: boolean;
}, {
    vars: Record<string, string>;
    formula: string;
    is_content?: boolean | undefined;
}>;
export type FormulaCookInput = z.infer<typeof FormulaCookInputSchema>;
/**
 * Schema for gt_formula_execute
 */
export declare const FormulaExecuteInputSchema: z.ZodObject<{
    /** Formula name */
    formula: z.ZodString;
    /** Variables for substitution */
    vars: z.ZodRecord<z.ZodString, z.ZodString>;
    /** Target agent for execution */
    target_agent: z.ZodOptional<z.ZodEnum<["polecat", "crew", "mayor", "refinery"]>>;
    /** Dry run (don\'t actually execute) */
    dry_run: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    vars: Record<string, string>;
    formula: string;
    dry_run: boolean;
    target_agent?: "mayor" | "polecat" | "refinery" | "crew" | undefined;
}, {
    vars: Record<string, string>;
    formula: string;
    target_agent?: "mayor" | "polecat" | "refinery" | "crew" | undefined;
    dry_run?: boolean | undefined;
}>;
export type FormulaExecuteInput = z.infer<typeof FormulaExecuteInputSchema>;
/**
 * Schema for gt_formula_create
 */
export declare const FormulaCreateInputSchema: z.ZodObject<{
    /** Formula name */
    name: z.ZodString;
    /** Formula type */
    type: z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>;
    /** Workflow steps */
    steps: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodString;
        description: z.ZodOptional<z.ZodString>;
        needs: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        title: string;
        description?: string | undefined;
        needs?: string[] | undefined;
    }, {
        id: string;
        title: string;
        description?: string | undefined;
        needs?: string[] | undefined;
    }>, "many">>;
    /** Variable definitions */
    vars: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodObject<{
        default: z.ZodOptional<z.ZodString>;
        description: z.ZodOptional<z.ZodString>;
        required: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
    }, {
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
    }>>>;
    /** Formula description */
    description: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    type: "convoy" | "workflow" | "expansion" | "aspect";
    description?: string | undefined;
    steps?: {
        id: string;
        title: string;
        description?: string | undefined;
        needs?: string[] | undefined;
    }[] | undefined;
    vars?: Record<string, {
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
    }> | undefined;
}, {
    name: string;
    type: "convoy" | "workflow" | "expansion" | "aspect";
    description?: string | undefined;
    steps?: {
        id: string;
        title: string;
        description?: string | undefined;
        needs?: string[] | undefined;
    }[] | undefined;
    vars?: Record<string, {
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
    }> | undefined;
}>;
export type FormulaCreateInput = z.infer<typeof FormulaCreateInputSchema>;
/**
 * Schema for gt_sling
 */
export declare const SlingInputSchema: z.ZodObject<{
    /** Bead ID to sling */
    bead_id: z.ZodString;
    /** Target agent type */
    target: z.ZodEnum<["polecat", "crew", "mayor"]>;
    /** Optional formula to use */
    formula: z.ZodOptional<z.ZodString>;
    /** Priority override */
    priority: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    target: "mayor" | "polecat" | "crew";
    bead_id: string;
    priority?: number | undefined;
    formula?: string | undefined;
}, {
    target: "mayor" | "polecat" | "crew";
    bead_id: string;
    priority?: number | undefined;
    formula?: string | undefined;
}>;
export type SlingInput = z.infer<typeof SlingInputSchema>;
/**
 * Schema for gt_agents
 */
export declare const AgentsInputSchema: z.ZodObject<{
    /** Filter by rig */
    rig: z.ZodOptional<z.ZodString>;
    /** Filter by role */
    role: z.ZodOptional<z.ZodEnum<["mayor", "polecat", "refinery", "witness", "deacon", "dog", "crew"]>>;
    /** Include inactive agents */
    include_inactive: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    include_inactive: boolean;
    rig?: string | undefined;
    role?: "mayor" | "polecat" | "refinery" | "witness" | "deacon" | "dog" | "crew" | undefined;
}, {
    rig?: string | undefined;
    role?: "mayor" | "polecat" | "refinery" | "witness" | "deacon" | "dog" | "crew" | undefined;
    include_inactive?: boolean | undefined;
}>;
export type AgentsInput = z.infer<typeof AgentsInputSchema>;
/**
 * Schema for gt_mail
 */
export declare const MailInputSchema: z.ZodObject<{
    /** Mail action */
    action: z.ZodEnum<["send", "read", "list"]>;
    /** Recipient (for send) */
    to: z.ZodOptional<z.ZodString>;
    /** Subject (for send) */
    subject: z.ZodOptional<z.ZodString>;
    /** Body (for send) */
    body: z.ZodOptional<z.ZodString>;
    /** Mail ID (for read) */
    mail_id: z.ZodOptional<z.ZodString>;
    /** Maximum messages to list */
    limit: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    limit: number;
    action: "send" | "read" | "list";
    to?: string | undefined;
    subject?: string | undefined;
    body?: string | undefined;
    mail_id?: string | undefined;
}, {
    action: "send" | "read" | "list";
    limit?: number | undefined;
    to?: string | undefined;
    subject?: string | undefined;
    body?: string | undefined;
    mail_id?: string | undefined;
}>;
export type MailInput = z.infer<typeof MailInputSchema>;
/**
 * Schema for gt_wasm_parse_formula
 */
export declare const WasmParseFormulaInputSchema: z.ZodObject<{
    /** TOML content to parse */
    content: z.ZodString;
    /** Validate against schema */
    validate: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    content: string;
    validate: boolean;
}, {
    content: string;
    validate?: boolean | undefined;
}>;
export type WasmParseFormulaInput = z.infer<typeof WasmParseFormulaInputSchema>;
/**
 * Schema for gt_wasm_resolve_deps
 */
export declare const WasmResolveDepsInputSchema: z.ZodObject<{
    /** Beads to analyze */
    beads: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        dependencies: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        dependencies?: string[] | undefined;
    }, {
        id: string;
        dependencies?: string[] | undefined;
    }>, "many">;
    /** Analysis action */
    action: z.ZodDefault<z.ZodEnum<["topo_sort", "critical_path", "cycle_detect"]>>;
}, "strip", z.ZodTypeAny, {
    beads: {
        id: string;
        dependencies?: string[] | undefined;
    }[];
    action: "topo_sort" | "cycle_detect" | "critical_path";
}, {
    beads: {
        id: string;
        dependencies?: string[] | undefined;
    }[];
    action?: "topo_sort" | "cycle_detect" | "critical_path" | undefined;
}>;
export type WasmResolveDepsInput = z.infer<typeof WasmResolveDepsInputSchema>;
/**
 * Schema for gt_wasm_cook_batch
 */
export declare const WasmCookBatchInputSchema: z.ZodObject<{
    /** Formulas to cook */
    formulas: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        content: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        name: string;
        content: string;
    }, {
        name: string;
        content: string;
    }>, "many">;
    /** Variables for each formula */
    vars: z.ZodArray<z.ZodRecord<z.ZodString, z.ZodString>, "many">;
    /** Continue on error */
    continue_on_error: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    formulas: {
        name: string;
        content: string;
    }[];
    vars: Record<string, string>[];
    continue_on_error: boolean;
}, {
    formulas: {
        name: string;
        content: string;
    }[];
    vars: Record<string, string>[];
    continue_on_error?: boolean | undefined;
}>;
export type WasmCookBatchInput = z.infer<typeof WasmCookBatchInputSchema>;
/**
 * Schema for gt_wasm_match_pattern
 */
export declare const WasmMatchPatternInputSchema: z.ZodObject<{
    /** Search query */
    query: z.ZodString;
    /** Candidate patterns to match against */
    candidates: z.ZodArray<z.ZodString, "many">;
    /** Number of results to return */
    k: z.ZodDefault<z.ZodNumber>;
    /** Minimum similarity threshold (0-1) */
    threshold: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    threshold: number;
    k: number;
    query: string;
    candidates: string[];
}, {
    query: string;
    candidates: string[];
    threshold?: number | undefined;
    k?: number | undefined;
}>;
export type WasmMatchPatternInput = z.infer<typeof WasmMatchPatternInputSchema>;
/**
 * Schema for gt_wasm_optimize_convoy
 */
export declare const WasmOptimizeConvoyInputSchema: z.ZodObject<{
    /** Convoy ID to optimize */
    convoy_id: z.ZodString;
    /** Optimization strategy */
    strategy: z.ZodDefault<z.ZodEnum<["parallel", "serial", "hybrid"]>>;
    /** Consider resource constraints */
    resource_constraints: z.ZodOptional<z.ZodObject<{
        max_parallel: z.ZodOptional<z.ZodNumber>;
        agent_capacity: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
    }, "strip", z.ZodTypeAny, {
        max_parallel?: number | undefined;
        agent_capacity?: Record<string, number> | undefined;
    }, {
        max_parallel?: number | undefined;
        agent_capacity?: Record<string, number> | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    strategy: "parallel" | "serial" | "hybrid";
    convoy_id: string;
    resource_constraints?: {
        max_parallel?: number | undefined;
        agent_capacity?: Record<string, number> | undefined;
    } | undefined;
}, {
    convoy_id: string;
    strategy?: "parallel" | "serial" | "hybrid" | undefined;
    resource_constraints?: {
        max_parallel?: number | undefined;
        agent_capacity?: Record<string, number> | undefined;
    } | undefined;
}>;
export type WasmOptimizeConvoyInput = z.infer<typeof WasmOptimizeConvoyInputSchema>;
/**
 * Result for bead creation
 */
export interface BeadCreateResult {
    success: boolean;
    bead: Bead;
    durationMs: number;
}
/**
 * Result for beads ready list
 */
export interface BeadsReadyResult {
    success: boolean;
    beads: Bead[];
    total: number;
    durationMs: number;
}
/**
 * Result for bead show
 */
export interface BeadShowResult {
    success: boolean;
    bead: Bead;
    dependencies: string[];
    dependents: string[];
    durationMs: number;
}
/**
 * Result for bead dependency operation
 */
export interface BeadDepResult {
    success: boolean;
    action: DepAction;
    child: string;
    parent: string;
    durationMs: number;
}
/**
 * Result for beads sync
 */
export interface BeadsSyncResult {
    success: boolean;
    direction: SyncDirection;
    pulled: number;
    pushed: number;
    conflicts: number;
    durationMs: number;
}
/**
 * Result for convoy creation
 */
export interface ConvoyCreateResult {
    success: boolean;
    convoy: Convoy;
    durationMs: number;
}
/**
 * Result for convoy status
 */
export interface ConvoyStatusResult {
    success: boolean;
    convoys: Convoy[];
    durationMs: number;
}
/**
 * Result for convoy track
 */
export interface ConvoyTrackResult {
    success: boolean;
    convoy_id: string;
    action: 'add' | 'remove';
    issues_modified: string[];
    durationMs: number;
}
/**
 * Result for formula list
 */
export interface FormulaListResult {
    success: boolean;
    formulas: Array<{
        name: string;
        type: FormulaType;
        description: string;
        builtin: boolean;
    }>;
    durationMs: number;
}
/**
 * Result for formula cook
 */
export interface FormulaCookResult {
    success: boolean;
    cooked: CookedFormula;
    wasmUsed: boolean;
    durationMs: number;
}
/**
 * Result for formula execute
 */
export interface FormulaExecuteResult {
    success: boolean;
    formula: string;
    beads_created: string[];
    target_agent?: string;
    dry_run: boolean;
    durationMs: number;
}
/**
 * Result for formula create
 */
export interface FormulaCreateResult {
    success: boolean;
    name: string;
    path: string;
    durationMs: number;
}
/**
 * Result for sling
 */
export interface SlingResult {
    success: boolean;
    bead_id: string;
    target: TargetAgent;
    formula_used?: string;
    durationMs: number;
}
/**
 * Result for agents list
 */
export interface AgentsResult {
    success: boolean;
    agents: GasTownAgent[];
    durationMs: number;
}
/**
 * Result for mail
 */
export interface MailResult {
    success: boolean;
    action: MailAction;
    messages?: GasTownMail[];
    sent_id?: string;
    durationMs: number;
}
/**
 * Result for WASM formula parse
 */
export interface WasmParseFormulaResult {
    success: boolean;
    ast: FormulaAST;
    wasmPerformanceMs: number;
    durationMs: number;
}
/**
 * Result for WASM dependency resolution
 */
export interface WasmResolveDepsResult {
    success: boolean;
    action: DependencyAction;
    result: DependencyResolution;
    wasmPerformanceMs: number;
    durationMs: number;
}
/**
 * Result for WASM batch cook
 */
export interface WasmCookBatchResult {
    success: boolean;
    cooked: CookedFormula[];
    errors: Array<{
        index: number;
        error: string;
    }>;
    wasmPerformanceMs: number;
    durationMs: number;
}
/**
 * Result for WASM pattern match
 */
export interface WasmMatchPatternResult {
    success: boolean;
    matches: PatternMatch[];
    wasmPerformanceMs: number;
    durationMs: number;
}
/**
 * Result for WASM convoy optimization
 */
export interface WasmOptimizeConvoyResult {
    success: boolean;
    optimization: ConvoyOptimization;
    wasmPerformanceMs: number;
    durationMs: number;
}
/**
 * MCP Tool: gt_beads_create
 *
 * Create a bead/issue in the Beads system
 */
export declare const beadsCreateTool: MCPTool<BeadsCreateInput, BeadCreateResult>;
/**
 * MCP Tool: gt_beads_ready
 *
 * List beads that are ready to work on (no blockers)
 */
export declare const beadsReadyTool: MCPTool<BeadsReadyInput, BeadsReadyResult>;
/**
 * MCP Tool: gt_beads_show
 *
 * Show detailed information about a specific bead
 */
export declare const beadsShowTool: MCPTool<BeadsShowInput, BeadShowResult>;
/**
 * MCP Tool: gt_beads_dep
 *
 * Manage bead dependencies (add/remove)
 */
export declare const beadsDepTool: MCPTool<BeadsDepInput, BeadDepResult>;
/**
 * MCP Tool: gt_beads_sync
 *
 * Sync beads with AgentDB (bidirectional)
 */
export declare const beadsSyncTool: MCPTool<BeadsSyncInput, BeadsSyncResult>;
/**
 * MCP Tool: gt_convoy_create
 *
 * Create a convoy (work order) for tracking multiple issues
 */
export declare const convoyCreateTool: MCPTool<ConvoyCreateInput, ConvoyCreateResult>;
/**
 * MCP Tool: gt_convoy_status
 *
 * Check convoy status (single or all)
 */
export declare const convoyStatusTool: MCPTool<ConvoyStatusInput, ConvoyStatusResult>;
/**
 * MCP Tool: gt_convoy_track
 *
 * Add or remove issues from a convoy
 */
export declare const convoyTrackTool: MCPTool<ConvoyTrackInput, ConvoyTrackResult>;
/**
 * MCP Tool: gt_formula_list
 *
 * List available formulas
 */
export declare const formulaListTool: MCPTool<FormulaListInput, FormulaListResult>;
/**
 * MCP Tool: gt_formula_cook
 *
 * Cook a formula with variable substitution (352x faster with WASM)
 */
export declare const formulaCookTool: MCPTool<FormulaCookInput, FormulaCookResult>;
/**
 * MCP Tool: gt_formula_execute
 *
 * Execute a formula (creates beads/molecules)
 */
export declare const formulaExecuteTool: MCPTool<FormulaExecuteInput, FormulaExecuteResult>;
/**
 * MCP Tool: gt_formula_create
 *
 * Create a custom formula
 */
export declare const formulaCreateTool: MCPTool<FormulaCreateInput, FormulaCreateResult>;
/**
 * MCP Tool: gt_sling
 *
 * Sling work to a Gas Town agent
 */
export declare const slingTool: MCPTool<SlingInput, SlingResult>;
/**
 * MCP Tool: gt_agents
 *
 * List Gas Town agents
 */
export declare const agentsTool: MCPTool<AgentsInput, AgentsResult>;
/**
 * MCP Tool: gt_mail
 *
 * Send/receive Gas Town mail
 */
export declare const mailTool: MCPTool<MailInput, MailResult>;
/**
 * MCP Tool: gt_wasm_parse_formula
 *
 * Parse TOML formula to AST (352x faster than JS)
 */
export declare const wasmParseFormulaTool: MCPTool<WasmParseFormulaInput, WasmParseFormulaResult>;
/**
 * MCP Tool: gt_wasm_resolve_deps
 *
 * Resolve dependency graph using WASM (150x faster than JS)
 */
export declare const wasmResolveDepsTool: MCPTool<WasmResolveDepsInput, WasmResolveDepsResult>;
/**
 * MCP Tool: gt_wasm_cook_batch
 *
 * Batch cook multiple formulas using WASM (352x faster than JS)
 */
export declare const wasmCookBatchTool: MCPTool<WasmCookBatchInput, WasmCookBatchResult>;
/**
 * MCP Tool: gt_wasm_match_pattern
 *
 * Find similar formulas/beads using WASM (150x-12500x faster with HNSW)
 */
export declare const wasmMatchPatternTool: MCPTool<WasmMatchPatternInput, WasmMatchPatternResult>;
/**
 * MCP Tool: gt_wasm_optimize_convoy
 *
 * Optimize convoy execution order using WASM (150x faster than JS)
 */
export declare const wasmOptimizeConvoyTool: MCPTool<WasmOptimizeConvoyInput, WasmOptimizeConvoyResult>;
/**
 * All Gas Town Bridge MCP Tools (20 total)
 */
export declare const gasTownBridgeTools: MCPTool[];
/**
 * Tool name to handler map
 */
export declare const toolHandlers: Map<string, (input: unknown, context: ToolContext) => Promise<MCPToolResult<unknown>>>;
/**
 * Tool categories for documentation
 */
export declare const toolCategories: {
    beads: string[];
    convoy: string[];
    formula: string[];
    orchestration: string[];
    wasm: string[];
};
/**
 * Get tool by name
 */
export declare function getTool(name: string): MCPTool | undefined;
/**
 * Get tools by layer
 */
export declare function getToolsByLayer(layer: 'cli' | 'wasm' | 'hybrid'): MCPTool[];
export default gasTownBridgeTools;
//# sourceMappingURL=mcp-tools.d.ts.map