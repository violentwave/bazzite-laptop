/**
 * Gas Town Bridge Plugin - Output Sanitizers
 *
 * Provides output sanitization for the Gas Town Bridge Plugin:
 * - sanitizeBeadOutput: Parse and sanitize bead CLI output
 * - sanitizeFormulaOutput: Parse and sanitize formula CLI output
 * - Remove sensitive data from outputs
 *
 * Security Features:
 * - JSON parsing with validation
 * - Sensitive field redaction (tokens, keys, passwords)
 * - Output size limits to prevent DoS
 * - Type coercion and validation
 *
 * All sanitizers follow OWASP guidelines for output encoding.
 *
 * @module gastown-bridge/sanitizers
 * @version 0.1.0
 */
import { z } from 'zod';
import type { Bead, Formula, Convoy } from './types.js';
/**
 * Maximum output sizes to prevent DoS
 */
declare const MAX_OUTPUT_SIZE: {
    readonly single: number;
    readonly list: number;
    readonly field: 65536;
};
/**
 * Sensitive field patterns that should be redacted
 */
declare const SENSITIVE_FIELD_PATTERNS: RegExp[];
/**
 * Fields that should always be removed from output
 */
declare const REDACTED_FIELDS: Set<string>;
/**
 * Schema for parsing raw bead output
 */
declare const RawBeadSchema: z.ZodObject<{
    id: z.ZodString;
    title: z.ZodDefault<z.ZodString>;
    description: z.ZodDefault<z.ZodString>;
    status: z.ZodDefault<z.ZodEnum<["open", "in_progress", "closed"]>>;
    priority: z.ZodDefault<z.ZodNumber>;
    labels: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    parentId: z.ZodOptional<z.ZodString>;
    parent_id: z.ZodOptional<z.ZodString>;
    createdAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    created_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    updatedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    updated_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    assignee: z.ZodOptional<z.ZodString>;
    rig: z.ZodOptional<z.ZodString>;
    blockedBy: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocked_by: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocks: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "passthrough", z.ZodTypeAny, z.objectOutputType<{
    id: z.ZodString;
    title: z.ZodDefault<z.ZodString>;
    description: z.ZodDefault<z.ZodString>;
    status: z.ZodDefault<z.ZodEnum<["open", "in_progress", "closed"]>>;
    priority: z.ZodDefault<z.ZodNumber>;
    labels: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    parentId: z.ZodOptional<z.ZodString>;
    parent_id: z.ZodOptional<z.ZodString>;
    createdAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    created_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    updatedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    updated_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    assignee: z.ZodOptional<z.ZodString>;
    rig: z.ZodOptional<z.ZodString>;
    blockedBy: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocked_by: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocks: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, z.ZodTypeAny, "passthrough">, z.objectInputType<{
    id: z.ZodString;
    title: z.ZodDefault<z.ZodString>;
    description: z.ZodDefault<z.ZodString>;
    status: z.ZodDefault<z.ZodEnum<["open", "in_progress", "closed"]>>;
    priority: z.ZodDefault<z.ZodNumber>;
    labels: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    parentId: z.ZodOptional<z.ZodString>;
    parent_id: z.ZodOptional<z.ZodString>;
    createdAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    created_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    updatedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    updated_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    assignee: z.ZodOptional<z.ZodString>;
    rig: z.ZodOptional<z.ZodString>;
    blockedBy: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocked_by: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    blocks: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, z.ZodTypeAny, "passthrough">>;
/**
 * Schema for parsing raw formula output
 */
declare const RawFormulaSchema: z.ZodObject<{
    name: z.ZodString;
    description: z.ZodDefault<z.ZodString>;
    type: z.ZodDefault<z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>>;
    version: z.ZodDefault<z.ZodNumber>;
    legs: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodDefault<z.ZodString>;
        focus: z.ZodDefault<z.ZodString>;
        description: z.ZodDefault<z.ZodString>;
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
        title?: string | undefined;
        description?: string | undefined;
        focus?: string | undefined;
        agent?: string | undefined;
        order?: number | undefined;
    }>, "many">>;
    steps: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodDefault<z.ZodString>;
        description: z.ZodDefault<z.ZodString>;
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
        title?: string | undefined;
        description?: string | undefined;
        needs?: string[] | undefined;
        duration?: number | undefined;
        requires?: string[] | undefined;
        metadata?: Record<string, unknown> | undefined;
    }>, "many">>;
    vars: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodObject<{
        name: z.ZodDefault<z.ZodString>;
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
        name?: string | undefined;
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
        pattern?: string | undefined;
        enum?: string[] | undefined;
    }>>>;
    synthesis: z.ZodOptional<z.ZodObject<{
        strategy: z.ZodDefault<z.ZodEnum<["merge", "sequential", "parallel"]>>;
        format: z.ZodOptional<z.ZodString>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    }, {
        description?: string | undefined;
        strategy?: "merge" | "sequential" | "parallel" | undefined;
        format?: string | undefined;
    }>>;
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
        name: z.ZodDefault<z.ZodString>;
        pointcut: z.ZodDefault<z.ZodString>;
        advice: z.ZodDefault<z.ZodString>;
        type: z.ZodDefault<z.ZodEnum<["before", "after", "around"]>>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }, {
        name?: string | undefined;
        type?: "before" | "after" | "around" | undefined;
        pointcut?: string | undefined;
        advice?: string | undefined;
    }>, "many">>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "passthrough", z.ZodTypeAny, z.objectOutputType<{
    name: z.ZodString;
    description: z.ZodDefault<z.ZodString>;
    type: z.ZodDefault<z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>>;
    version: z.ZodDefault<z.ZodNumber>;
    legs: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodDefault<z.ZodString>;
        focus: z.ZodDefault<z.ZodString>;
        description: z.ZodDefault<z.ZodString>;
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
        title?: string | undefined;
        description?: string | undefined;
        focus?: string | undefined;
        agent?: string | undefined;
        order?: number | undefined;
    }>, "many">>;
    steps: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodDefault<z.ZodString>;
        description: z.ZodDefault<z.ZodString>;
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
        title?: string | undefined;
        description?: string | undefined;
        needs?: string[] | undefined;
        duration?: number | undefined;
        requires?: string[] | undefined;
        metadata?: Record<string, unknown> | undefined;
    }>, "many">>;
    vars: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodObject<{
        name: z.ZodDefault<z.ZodString>;
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
        name?: string | undefined;
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
        pattern?: string | undefined;
        enum?: string[] | undefined;
    }>>>;
    synthesis: z.ZodOptional<z.ZodObject<{
        strategy: z.ZodDefault<z.ZodEnum<["merge", "sequential", "parallel"]>>;
        format: z.ZodOptional<z.ZodString>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    }, {
        description?: string | undefined;
        strategy?: "merge" | "sequential" | "parallel" | undefined;
        format?: string | undefined;
    }>>;
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
        name: z.ZodDefault<z.ZodString>;
        pointcut: z.ZodDefault<z.ZodString>;
        advice: z.ZodDefault<z.ZodString>;
        type: z.ZodDefault<z.ZodEnum<["before", "after", "around"]>>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }, {
        name?: string | undefined;
        type?: "before" | "after" | "around" | undefined;
        pointcut?: string | undefined;
        advice?: string | undefined;
    }>, "many">>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, z.ZodTypeAny, "passthrough">, z.objectInputType<{
    name: z.ZodString;
    description: z.ZodDefault<z.ZodString>;
    type: z.ZodDefault<z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>>;
    version: z.ZodDefault<z.ZodNumber>;
    legs: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodDefault<z.ZodString>;
        focus: z.ZodDefault<z.ZodString>;
        description: z.ZodDefault<z.ZodString>;
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
        title?: string | undefined;
        description?: string | undefined;
        focus?: string | undefined;
        agent?: string | undefined;
        order?: number | undefined;
    }>, "many">>;
    steps: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        title: z.ZodDefault<z.ZodString>;
        description: z.ZodDefault<z.ZodString>;
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
        title?: string | undefined;
        description?: string | undefined;
        needs?: string[] | undefined;
        duration?: number | undefined;
        requires?: string[] | undefined;
        metadata?: Record<string, unknown> | undefined;
    }>, "many">>;
    vars: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodObject<{
        name: z.ZodDefault<z.ZodString>;
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
        name?: string | undefined;
        description?: string | undefined;
        default?: string | undefined;
        required?: boolean | undefined;
        pattern?: string | undefined;
        enum?: string[] | undefined;
    }>>>;
    synthesis: z.ZodOptional<z.ZodObject<{
        strategy: z.ZodDefault<z.ZodEnum<["merge", "sequential", "parallel"]>>;
        format: z.ZodOptional<z.ZodString>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        strategy: "merge" | "sequential" | "parallel";
        description?: string | undefined;
        format?: string | undefined;
    }, {
        description?: string | undefined;
        strategy?: "merge" | "sequential" | "parallel" | undefined;
        format?: string | undefined;
    }>>;
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
        name: z.ZodDefault<z.ZodString>;
        pointcut: z.ZodDefault<z.ZodString>;
        advice: z.ZodDefault<z.ZodString>;
        type: z.ZodDefault<z.ZodEnum<["before", "after", "around"]>>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        type: "before" | "after" | "around";
        pointcut: string;
        advice: string;
    }, {
        name?: string | undefined;
        type?: "before" | "after" | "around" | undefined;
        pointcut?: string | undefined;
        advice?: string | undefined;
    }>, "many">>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, z.ZodTypeAny, "passthrough">>;
/**
 * Schema for parsing raw convoy output
 */
declare const RawConvoySchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    trackedIssues: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    tracked_issues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    status: z.ZodDefault<z.ZodEnum<["active", "landed", "failed", "paused"]>>;
    startedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    started_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    completedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    completed_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    progress: z.ZodDefault<z.ZodObject<{
        total: z.ZodDefault<z.ZodNumber>;
        closed: z.ZodDefault<z.ZodNumber>;
        inProgress: z.ZodDefault<z.ZodNumber>;
        in_progress: z.ZodOptional<z.ZodNumber>;
        blocked: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        closed: number;
        total: number;
        inProgress: number;
        blocked: number;
        in_progress?: number | undefined;
    }, {
        in_progress?: number | undefined;
        closed?: number | undefined;
        total?: number | undefined;
        inProgress?: number | undefined;
        blocked?: number | undefined;
    }>>;
    formula: z.ZodOptional<z.ZodString>;
    description: z.ZodOptional<z.ZodString>;
}, "passthrough", z.ZodTypeAny, z.objectOutputType<{
    id: z.ZodString;
    name: z.ZodString;
    trackedIssues: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    tracked_issues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    status: z.ZodDefault<z.ZodEnum<["active", "landed", "failed", "paused"]>>;
    startedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    started_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    completedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    completed_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    progress: z.ZodDefault<z.ZodObject<{
        total: z.ZodDefault<z.ZodNumber>;
        closed: z.ZodDefault<z.ZodNumber>;
        inProgress: z.ZodDefault<z.ZodNumber>;
        in_progress: z.ZodOptional<z.ZodNumber>;
        blocked: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        closed: number;
        total: number;
        inProgress: number;
        blocked: number;
        in_progress?: number | undefined;
    }, {
        in_progress?: number | undefined;
        closed?: number | undefined;
        total?: number | undefined;
        inProgress?: number | undefined;
        blocked?: number | undefined;
    }>>;
    formula: z.ZodOptional<z.ZodString>;
    description: z.ZodOptional<z.ZodString>;
}, z.ZodTypeAny, "passthrough">, z.objectInputType<{
    id: z.ZodString;
    name: z.ZodString;
    trackedIssues: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    tracked_issues: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    status: z.ZodDefault<z.ZodEnum<["active", "landed", "failed", "paused"]>>;
    startedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    started_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    completedAt: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    completed_at: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodDate]>>;
    progress: z.ZodDefault<z.ZodObject<{
        total: z.ZodDefault<z.ZodNumber>;
        closed: z.ZodDefault<z.ZodNumber>;
        inProgress: z.ZodDefault<z.ZodNumber>;
        in_progress: z.ZodOptional<z.ZodNumber>;
        blocked: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        closed: number;
        total: number;
        inProgress: number;
        blocked: number;
        in_progress?: number | undefined;
    }, {
        in_progress?: number | undefined;
        closed?: number | undefined;
        total?: number | undefined;
        inProgress?: number | undefined;
        blocked?: number | undefined;
    }>>;
    formula: z.ZodOptional<z.ZodString>;
    description: z.ZodOptional<z.ZodString>;
}, z.ZodTypeAny, "passthrough">>;
/**
 * Sanitize raw bead output from CLI
 *
 * Parses JSON output, validates structure, redacts sensitive fields,
 * and normalizes the data to the Bead interface.
 *
 * @param raw - Raw string output from CLI
 * @returns Sanitized Bead object
 * @throws {BeadsError} If parsing or validation fails
 *
 * @example
 * ```typescript
 * const bead = sanitizeBeadOutput('{"id":"gt-abc12","title":"Test"}');
 * console.log(bead.id);  // 'gt-abc12'
 * ```
 */
export declare function sanitizeBeadOutput(raw: string): Bead;
/**
 * Sanitize raw formula output from CLI
 *
 * Parses JSON/TOML output, validates structure, redacts sensitive fields,
 * and normalizes the data to the Formula interface.
 *
 * @param raw - Raw string output from CLI
 * @returns Sanitized Formula object
 * @throws {FormulaError} If parsing or validation fails
 *
 * @example
 * ```typescript
 * const formula = sanitizeFormulaOutput('{"name":"test","type":"workflow"}');
 * console.log(formula.name);  // 'test'
 * ```
 */
export declare function sanitizeFormulaOutput(raw: string): Formula;
/**
 * Sanitize raw convoy output from CLI
 *
 * @param raw - Raw string output from CLI
 * @returns Sanitized Convoy object
 * @throws {ConvoyError} If parsing or validation fails
 */
export declare function sanitizeConvoyOutput(raw: string): Convoy;
/**
 * Sanitize a list of beads from JSONL output
 *
 * @param raw - Raw JSONL string (one JSON object per line)
 * @returns Array of sanitized Bead objects
 */
export declare function sanitizeBeadsListOutput(raw: string): Bead[];
/**
 * Recursively redact sensitive fields from an object
 */
declare function redactSensitiveFields(obj: Record<string, unknown>): void;
/**
 * Sanitize a string value with length limit
 */
declare function sanitizeString(value: string | undefined | null, maxLength: number): string;
/**
 * Sanitize a path value (remove traversal sequences)
 */
declare function sanitizePath(value: string): string;
/**
 * Parse a date value
 */
declare function parseDate(value: string | Date | undefined | null): Date | undefined;
/**
 * Sanitize metadata object
 */
declare function sanitizeMetadata(metadata: Record<string, unknown>): Record<string, unknown>;
export { MAX_OUTPUT_SIZE, SENSITIVE_FIELD_PATTERNS, REDACTED_FIELDS, RawBeadSchema, RawFormulaSchema, RawConvoySchema, redactSensitiveFields, sanitizeString, sanitizePath, parseDate, sanitizeMetadata, };
//# sourceMappingURL=sanitizers.d.ts.map