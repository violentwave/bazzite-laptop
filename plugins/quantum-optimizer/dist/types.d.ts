/**
 * Quantum Optimizer Plugin - Type Definitions
 *
 * Types for quantum-inspired optimization including QUBO problems,
 * annealing parameters, QAOA circuits, and Grover search.
 */
import { z } from 'zod';
/**
 * Quadratic Unconstrained Binary Optimization problem
 */
export interface QUBOProblem {
    /** Problem type identifier */
    readonly type: 'qubo' | 'ising' | 'sat' | 'max_cut' | 'tsp' | 'dependency';
    /** Number of binary variables */
    readonly variables: number;
    /** Linear coefficients (diagonal of Q matrix) */
    readonly linear: Float32Array;
    /** Quadratic coefficients (upper triangular of Q matrix, flattened) */
    readonly quadratic: Float32Array;
    /** Optional constraint violations penalty */
    readonly penalty?: number;
}
/**
 * QUBO solution
 */
export interface QUBOSolution {
    /** Binary assignment (0 or 1 for each variable) */
    readonly assignment: Uint8Array;
    /** Energy/cost of the solution */
    readonly energy: number;
    /** Whether this is optimal (or best found) */
    readonly optimal: boolean;
    /** Number of iterations/reads performed */
    readonly iterations: number;
    /** Confidence in optimality */
    readonly confidence: number;
}
/**
 * Temperature schedule for annealing
 */
export interface TemperatureSchedule {
    /** Initial temperature */
    readonly initial: number;
    /** Final temperature */
    readonly final: number;
    /** Schedule type */
    readonly type: 'linear' | 'exponential' | 'logarithmic' | 'adaptive';
}
/**
 * Annealing configuration
 */
export interface AnnealingConfig {
    /** Number of independent runs */
    readonly numReads: number;
    /** Total annealing time (abstract units) */
    readonly annealingTime: number;
    /** Chain strength for embedding */
    readonly chainStrength: number;
    /** Temperature schedule */
    readonly temperature: TemperatureSchedule;
    /** Embedding strategy */
    readonly embedding: 'auto' | 'minor' | 'pegasus' | 'chimera';
}
/**
 * Annealing result
 */
export interface AnnealingResult {
    /** Best solution found */
    readonly solution: QUBOSolution;
    /** All solutions found (sorted by energy) */
    readonly samples: QUBOSolution[];
    /** Energy histogram */
    readonly energyHistogram: Map<number, number>;
    /** Timing information */
    readonly timing: {
        readonly totalMs: number;
        readonly annealingMs: number;
        readonly embeddingMs: number;
    };
}
/**
 * Problem graph for QAOA
 */
export interface ProblemGraph {
    /** Number of nodes */
    readonly nodes: number;
    /** Edges as [source, target] pairs */
    readonly edges: ReadonlyArray<readonly [number, number]>;
    /** Edge weights (optional) */
    readonly weights?: Float32Array;
}
/**
 * QAOA circuit configuration
 */
export interface QAOACircuit {
    /** Circuit depth (p parameter) */
    readonly depth: number;
    /** Classical optimizer */
    readonly optimizer: 'cobyla' | 'bfgs' | 'adam' | 'nelder-mead';
    /** Initial parameter strategy */
    readonly initialParams: 'random' | 'heuristic' | 'transfer' | 'fourier';
    /** Number of measurement shots */
    readonly shots: number;
}
/**
 * QAOA result
 */
export interface QAOAResult {
    /** Best solution found */
    readonly solution: QUBOSolution;
    /** Optimal variational parameters (gamma, beta) */
    readonly parameters: {
        readonly gamma: Float32Array;
        readonly beta: Float32Array;
    };
    /** Approximation ratio (solution / optimal) */
    readonly approximationRatio: number;
    /** Convergence history */
    readonly convergence: Float32Array;
}
/**
 * Search space configuration
 */
export interface SearchSpace {
    /** Size of search space (N) */
    readonly size: number;
    /** Oracle predicate definition (safe expression) */
    readonly oracle: string;
    /** Structure of search space */
    readonly structure: 'unstructured' | 'database' | 'tree' | 'graph';
}
/**
 * Amplification configuration
 */
export interface AmplificationConfig {
    /** Amplification method */
    readonly method: 'standard' | 'fixed_point' | 'robust';
    /** Boost factor for robust amplification */
    readonly boostFactor?: number;
}
/**
 * Grover search result
 */
export interface GroverResult {
    /** Found solution(s) */
    readonly solutions: Uint8Array[];
    /** Number of oracle queries */
    readonly queries: number;
    /** Theoretical optimal queries (pi/4 * sqrt(N/M)) */
    readonly optimalQueries: number;
    /** Success probability */
    readonly successProbability: number;
}
/**
 * Package descriptor for dependency resolution
 */
export interface PackageDescriptor {
    /** Package name */
    readonly name: string;
    /** Version string */
    readonly version: string;
    /** Dependencies as name -> version constraint */
    readonly dependencies: Record<string, string>;
    /** Conflicting packages */
    readonly conflicts: ReadonlyArray<string>;
    /** Package size in KB */
    readonly size?: number;
    /** Known vulnerabilities */
    readonly vulnerabilities?: ReadonlyArray<string>;
}
/**
 * Dependency resolution constraints
 */
export interface DependencyConstraints {
    /** Optimization objective */
    readonly minimize: 'versions' | 'size' | 'vulnerabilities' | 'depth';
    /** Existing lockfile constraints */
    readonly lockfile?: Record<string, string>;
    /** Include peer dependencies */
    readonly includePeer: boolean;
    /** Maximum resolution time in ms */
    readonly timeout: number;
}
/**
 * Dependency resolution result
 */
export interface DependencyResult {
    /** Resolved package versions */
    readonly resolved: Record<string, string>;
    /** Installation order */
    readonly order: ReadonlyArray<string>;
    /** Conflicts that were resolved */
    readonly resolvedConflicts: ReadonlyArray<{
        readonly packages: [string, string];
        readonly resolution: string;
    }>;
    /** Total size if calculated */
    readonly totalSize?: number;
    /** Remaining vulnerabilities */
    readonly vulnerabilities?: ReadonlyArray<string>;
}
/**
 * Task for scheduling
 */
export interface ScheduleTask {
    /** Unique task ID */
    readonly id: string;
    /** Task duration in time units */
    readonly duration: number;
    /** Prerequisite task IDs */
    readonly dependencies: ReadonlyArray<string>;
    /** Required resources */
    readonly resources: ReadonlyArray<string>;
    /** Optional deadline */
    readonly deadline?: number;
    /** Priority (higher = more important) */
    readonly priority?: number;
}
/**
 * Resource for scheduling
 */
export interface ScheduleResource {
    /** Unique resource ID */
    readonly id: string;
    /** Maximum concurrent usage */
    readonly capacity: number;
    /** Cost per time unit */
    readonly cost: number;
    /** Availability windows */
    readonly availability?: ReadonlyArray<{
        readonly start: number;
        readonly end: number;
    }>;
}
/**
 * Schedule optimization objective
 */
export type ScheduleObjective = 'makespan' | 'cost' | 'utilization' | 'weighted';
/**
 * Scheduled task assignment
 */
export interface ScheduledTask {
    /** Task ID */
    readonly taskId: string;
    /** Start time */
    readonly start: number;
    /** End time */
    readonly end: number;
    /** Assigned resources */
    readonly resources: ReadonlyArray<string>;
}
/**
 * Schedule optimization result
 */
export interface ScheduleResult {
    /** Scheduled tasks */
    readonly schedule: ReadonlyArray<ScheduledTask>;
    /** Total makespan */
    readonly makespan: number;
    /** Total cost */
    readonly cost: number;
    /** Resource utilization per resource */
    readonly utilization: Record<string, number>;
    /** Critical path */
    readonly criticalPath: ReadonlyArray<string>;
    /** Optimization score */
    readonly score: number;
}
export declare const TemperatureScheduleSchema: z.ZodObject<{
    initial: z.ZodDefault<z.ZodNumber>;
    final: z.ZodDefault<z.ZodNumber>;
    type: z.ZodDefault<z.ZodEnum<["linear", "exponential", "logarithmic", "adaptive"]>>;
}, "strip", z.ZodTypeAny, {
    initial: number;
    final: number;
    type: "linear" | "exponential" | "logarithmic" | "adaptive";
}, {
    initial?: number | undefined;
    final?: number | undefined;
    type?: "linear" | "exponential" | "logarithmic" | "adaptive" | undefined;
}>;
export declare const AnnealingSolveInputSchema: z.ZodObject<{
    problem: z.ZodObject<{
        type: z.ZodEnum<["qubo", "ising", "sat", "max_cut", "tsp", "dependency"]>;
        variables: z.ZodNumber;
        constraints: z.ZodOptional<z.ZodArray<z.ZodUnknown, "many">>;
        objective: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        linear: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
        quadratic: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
    }, "strip", z.ZodTypeAny, {
        type: "qubo" | "ising" | "sat" | "max_cut" | "tsp" | "dependency";
        variables: number;
        linear?: number[] | undefined;
        constraints?: unknown[] | undefined;
        objective?: Record<string, number> | undefined;
        quadratic?: number[] | undefined;
    }, {
        type: "qubo" | "ising" | "sat" | "max_cut" | "tsp" | "dependency";
        variables: number;
        linear?: number[] | undefined;
        constraints?: unknown[] | undefined;
        objective?: Record<string, number> | undefined;
        quadratic?: number[] | undefined;
    }>;
    parameters: z.ZodOptional<z.ZodObject<{
        numReads: z.ZodDefault<z.ZodNumber>;
        annealingTime: z.ZodDefault<z.ZodNumber>;
        chainStrength: z.ZodDefault<z.ZodNumber>;
        temperature: z.ZodOptional<z.ZodObject<{
            initial: z.ZodDefault<z.ZodNumber>;
            final: z.ZodDefault<z.ZodNumber>;
            type: z.ZodDefault<z.ZodEnum<["linear", "exponential", "logarithmic", "adaptive"]>>;
        }, "strip", z.ZodTypeAny, {
            initial: number;
            final: number;
            type: "linear" | "exponential" | "logarithmic" | "adaptive";
        }, {
            initial?: number | undefined;
            final?: number | undefined;
            type?: "linear" | "exponential" | "logarithmic" | "adaptive" | undefined;
        }>>;
    }, "strip", z.ZodTypeAny, {
        numReads: number;
        annealingTime: number;
        chainStrength: number;
        temperature?: {
            initial: number;
            final: number;
            type: "linear" | "exponential" | "logarithmic" | "adaptive";
        } | undefined;
    }, {
        numReads?: number | undefined;
        annealingTime?: number | undefined;
        chainStrength?: number | undefined;
        temperature?: {
            initial?: number | undefined;
            final?: number | undefined;
            type?: "linear" | "exponential" | "logarithmic" | "adaptive" | undefined;
        } | undefined;
    }>>;
    embedding: z.ZodDefault<z.ZodEnum<["auto", "minor", "pegasus", "chimera"]>>;
}, "strip", z.ZodTypeAny, {
    problem: {
        type: "qubo" | "ising" | "sat" | "max_cut" | "tsp" | "dependency";
        variables: number;
        linear?: number[] | undefined;
        constraints?: unknown[] | undefined;
        objective?: Record<string, number> | undefined;
        quadratic?: number[] | undefined;
    };
    embedding: "auto" | "minor" | "pegasus" | "chimera";
    parameters?: {
        numReads: number;
        annealingTime: number;
        chainStrength: number;
        temperature?: {
            initial: number;
            final: number;
            type: "linear" | "exponential" | "logarithmic" | "adaptive";
        } | undefined;
    } | undefined;
}, {
    problem: {
        type: "qubo" | "ising" | "sat" | "max_cut" | "tsp" | "dependency";
        variables: number;
        linear?: number[] | undefined;
        constraints?: unknown[] | undefined;
        objective?: Record<string, number> | undefined;
        quadratic?: number[] | undefined;
    };
    parameters?: {
        numReads?: number | undefined;
        annealingTime?: number | undefined;
        chainStrength?: number | undefined;
        temperature?: {
            initial?: number | undefined;
            final?: number | undefined;
            type?: "linear" | "exponential" | "logarithmic" | "adaptive" | undefined;
        } | undefined;
    } | undefined;
    embedding?: "auto" | "minor" | "pegasus" | "chimera" | undefined;
}>;
export type AnnealingSolveInput = z.infer<typeof AnnealingSolveInputSchema>;
export declare const QAOAOptimizeInputSchema: z.ZodObject<{
    problem: z.ZodObject<{
        type: z.ZodEnum<["max_cut", "portfolio", "scheduling", "routing"]>;
        graph: z.ZodObject<{
            nodes: z.ZodNumber;
            edges: z.ZodArray<z.ZodTuple<[z.ZodNumber, z.ZodNumber], null>, "many">;
            weights: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
        }, "strip", z.ZodTypeAny, {
            nodes: number;
            edges: [number, number][];
            weights?: number[] | undefined;
        }, {
            nodes: number;
            edges: [number, number][];
            weights?: number[] | undefined;
        }>;
    }, "strip", z.ZodTypeAny, {
        graph: {
            nodes: number;
            edges: [number, number][];
            weights?: number[] | undefined;
        };
        type: "max_cut" | "portfolio" | "scheduling" | "routing";
    }, {
        graph: {
            nodes: number;
            edges: [number, number][];
            weights?: number[] | undefined;
        };
        type: "max_cut" | "portfolio" | "scheduling" | "routing";
    }>;
    circuit: z.ZodOptional<z.ZodObject<{
        depth: z.ZodDefault<z.ZodNumber>;
        optimizer: z.ZodDefault<z.ZodEnum<["cobyla", "bfgs", "adam", "nelder-mead"]>>;
        initialParams: z.ZodDefault<z.ZodEnum<["random", "heuristic", "transfer", "fourier"]>>;
    }, "strip", z.ZodTypeAny, {
        depth: number;
        optimizer: "cobyla" | "bfgs" | "adam" | "nelder-mead";
        initialParams: "random" | "heuristic" | "transfer" | "fourier";
    }, {
        depth?: number | undefined;
        optimizer?: "cobyla" | "bfgs" | "adam" | "nelder-mead" | undefined;
        initialParams?: "random" | "heuristic" | "transfer" | "fourier" | undefined;
    }>>;
    shots: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    problem: {
        graph: {
            nodes: number;
            edges: [number, number][];
            weights?: number[] | undefined;
        };
        type: "max_cut" | "portfolio" | "scheduling" | "routing";
    };
    shots: number;
    circuit?: {
        depth: number;
        optimizer: "cobyla" | "bfgs" | "adam" | "nelder-mead";
        initialParams: "random" | "heuristic" | "transfer" | "fourier";
    } | undefined;
}, {
    problem: {
        graph: {
            nodes: number;
            edges: [number, number][];
            weights?: number[] | undefined;
        };
        type: "max_cut" | "portfolio" | "scheduling" | "routing";
    };
    circuit?: {
        depth?: number | undefined;
        optimizer?: "cobyla" | "bfgs" | "adam" | "nelder-mead" | undefined;
        initialParams?: "random" | "heuristic" | "transfer" | "fourier" | undefined;
    } | undefined;
    shots?: number | undefined;
}>;
export type QAOAOptimizeInput = z.infer<typeof QAOAOptimizeInputSchema>;
export declare const GroverSearchInputSchema: z.ZodObject<{
    searchSpace: z.ZodObject<{
        size: z.ZodNumber;
        oracle: z.ZodString;
        structure: z.ZodEnum<["unstructured", "database", "tree", "graph"]>;
    }, "strip", z.ZodTypeAny, {
        size: number;
        oracle: string;
        structure: "unstructured" | "database" | "tree" | "graph";
    }, {
        size: number;
        oracle: string;
        structure: "unstructured" | "database" | "tree" | "graph";
    }>;
    targets: z.ZodDefault<z.ZodNumber>;
    iterations: z.ZodDefault<z.ZodEnum<["optimal", "fixed", "adaptive"]>>;
    amplification: z.ZodOptional<z.ZodObject<{
        method: z.ZodDefault<z.ZodEnum<["standard", "fixed_point", "robust"]>>;
        boostFactor: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        method: "standard" | "fixed_point" | "robust";
        boostFactor?: number | undefined;
    }, {
        method?: "standard" | "fixed_point" | "robust" | undefined;
        boostFactor?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    searchSpace: {
        size: number;
        oracle: string;
        structure: "unstructured" | "database" | "tree" | "graph";
    };
    targets: number;
    iterations: "adaptive" | "optimal" | "fixed";
    amplification?: {
        method: "standard" | "fixed_point" | "robust";
        boostFactor?: number | undefined;
    } | undefined;
}, {
    searchSpace: {
        size: number;
        oracle: string;
        structure: "unstructured" | "database" | "tree" | "graph";
    };
    targets?: number | undefined;
    iterations?: "adaptive" | "optimal" | "fixed" | undefined;
    amplification?: {
        method?: "standard" | "fixed_point" | "robust" | undefined;
        boostFactor?: number | undefined;
    } | undefined;
}>;
export type GroverSearchInput = z.infer<typeof GroverSearchInputSchema>;
export declare const DependencyResolveInputSchema: z.ZodObject<{
    packages: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        version: z.ZodString;
        dependencies: z.ZodDefault<z.ZodRecord<z.ZodString, z.ZodString>>;
        conflicts: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
        size: z.ZodOptional<z.ZodNumber>;
        vulnerabilities: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        version: string;
        dependencies: Record<string, string>;
        conflicts: string[];
        size?: number | undefined;
        vulnerabilities?: string[] | undefined;
    }, {
        name: string;
        version: string;
        size?: number | undefined;
        vulnerabilities?: string[] | undefined;
        dependencies?: Record<string, string> | undefined;
        conflicts?: string[] | undefined;
    }>, "many">;
    constraints: z.ZodOptional<z.ZodObject<{
        minimize: z.ZodDefault<z.ZodEnum<["versions", "size", "vulnerabilities", "depth"]>>;
        lockfile: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodString>>;
        includePeer: z.ZodDefault<z.ZodBoolean>;
        timeout: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        minimize: "versions" | "size" | "vulnerabilities" | "depth";
        includePeer: boolean;
        timeout: number;
        lockfile?: Record<string, string> | undefined;
    }, {
        minimize?: "versions" | "size" | "vulnerabilities" | "depth" | undefined;
        lockfile?: Record<string, string> | undefined;
        includePeer?: boolean | undefined;
        timeout?: number | undefined;
    }>>;
    solver: z.ZodDefault<z.ZodEnum<["quantum_annealing", "qaoa", "hybrid"]>>;
}, "strip", z.ZodTypeAny, {
    packages: {
        name: string;
        version: string;
        dependencies: Record<string, string>;
        conflicts: string[];
        size?: number | undefined;
        vulnerabilities?: string[] | undefined;
    }[];
    solver: "quantum_annealing" | "qaoa" | "hybrid";
    constraints?: {
        minimize: "versions" | "size" | "vulnerabilities" | "depth";
        includePeer: boolean;
        timeout: number;
        lockfile?: Record<string, string> | undefined;
    } | undefined;
}, {
    packages: {
        name: string;
        version: string;
        size?: number | undefined;
        vulnerabilities?: string[] | undefined;
        dependencies?: Record<string, string> | undefined;
        conflicts?: string[] | undefined;
    }[];
    constraints?: {
        minimize?: "versions" | "size" | "vulnerabilities" | "depth" | undefined;
        lockfile?: Record<string, string> | undefined;
        includePeer?: boolean | undefined;
        timeout?: number | undefined;
    } | undefined;
    solver?: "quantum_annealing" | "qaoa" | "hybrid" | undefined;
}>;
export type DependencyResolveInput = z.infer<typeof DependencyResolveInputSchema>;
export declare const ScheduleOptimizeInputSchema: z.ZodObject<{
    tasks: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        duration: z.ZodNumber;
        dependencies: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
        resources: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
        deadline: z.ZodOptional<z.ZodNumber>;
        priority: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        dependencies: string[];
        id: string;
        duration: number;
        resources: string[];
        deadline?: number | undefined;
        priority?: number | undefined;
    }, {
        id: string;
        duration: number;
        dependencies?: string[] | undefined;
        resources?: string[] | undefined;
        deadline?: number | undefined;
        priority?: number | undefined;
    }>, "many">;
    resources: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        capacity: z.ZodNumber;
        cost: z.ZodNumber;
        availability: z.ZodOptional<z.ZodArray<z.ZodObject<{
            start: z.ZodNumber;
            end: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            start: number;
            end: number;
        }, {
            start: number;
            end: number;
        }>, "many">>;
    }, "strip", z.ZodTypeAny, {
        cost: number;
        id: string;
        capacity: number;
        availability?: {
            start: number;
            end: number;
        }[] | undefined;
    }, {
        cost: number;
        id: string;
        capacity: number;
        availability?: {
            start: number;
            end: number;
        }[] | undefined;
    }>, "many">;
    objective: z.ZodDefault<z.ZodEnum<["makespan", "cost", "utilization", "weighted"]>>;
    weights: z.ZodOptional<z.ZodObject<{
        makespan: z.ZodDefault<z.ZodNumber>;
        cost: z.ZodDefault<z.ZodNumber>;
        utilization: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        makespan: number;
        cost: number;
        utilization: number;
    }, {
        makespan?: number | undefined;
        cost?: number | undefined;
        utilization?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    objective: "makespan" | "cost" | "utilization" | "weighted";
    resources: {
        cost: number;
        id: string;
        capacity: number;
        availability?: {
            start: number;
            end: number;
        }[] | undefined;
    }[];
    tasks: {
        dependencies: string[];
        id: string;
        duration: number;
        resources: string[];
        deadline?: number | undefined;
        priority?: number | undefined;
    }[];
    weights?: {
        makespan: number;
        cost: number;
        utilization: number;
    } | undefined;
}, {
    resources: {
        cost: number;
        id: string;
        capacity: number;
        availability?: {
            start: number;
            end: number;
        }[] | undefined;
    }[];
    tasks: {
        id: string;
        duration: number;
        dependencies?: string[] | undefined;
        resources?: string[] | undefined;
        deadline?: number | undefined;
        priority?: number | undefined;
    }[];
    objective?: "makespan" | "cost" | "utilization" | "weighted" | undefined;
    weights?: {
        makespan?: number | undefined;
        cost?: number | undefined;
        utilization?: number | undefined;
    } | undefined;
}>;
export type ScheduleOptimizeInput = z.infer<typeof ScheduleOptimizeInputSchema>;
export interface MCPToolInputSchema {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
}
export interface MCPToolResult {
    content: Array<{
        type: 'text' | 'image' | 'resource';
        text?: string;
        data?: string;
        mimeType?: string;
    }>;
    isError?: boolean;
}
export interface MCPTool {
    name: string;
    description: string;
    inputSchema: MCPToolInputSchema;
    category?: string;
    tags?: string[];
    version?: string;
    cacheable?: boolean;
    cacheTTL?: number;
    handler: (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>;
}
export interface Logger {
    debug(message: string, meta?: Record<string, unknown>): void;
    info(message: string, meta?: Record<string, unknown>): void;
    warn(message: string, meta?: Record<string, unknown>): void;
    error(message: string, meta?: Record<string, unknown>): void;
}
export interface QuantumOptimizerConfig {
    annealing: {
        defaultReads: number;
        maxVariables: number;
        timeout: number;
    };
    qaoa: {
        maxDepth: number;
        maxNodes: number;
        defaultShots: number;
    };
    grover: {
        maxSearchSpace: number;
        allowedOracleOps: string[];
    };
    resourceLimits: {
        maxMemoryBytes: number;
        maxCpuTimeMs: number;
        maxIterations: number;
    };
}
export interface QuantumOptimizerBridge {
    initialized: boolean;
    initialize(): Promise<void>;
    dispose(): Promise<void>;
    solveQubo(problem: QUBOProblem, config: AnnealingConfig): Promise<AnnealingResult>;
    runQaoa(graph: ProblemGraph, circuit: QAOACircuit): Promise<QAOAResult>;
    groverSearch(space: SearchSpace, config: AmplificationConfig): Promise<GroverResult>;
}
export interface ToolContext {
    bridge?: QuantumOptimizerBridge;
    config?: QuantumOptimizerConfig;
    logger?: Logger;
}
/**
 * Create a successful MCP tool result
 */
export declare function successResult(data: unknown): MCPToolResult;
/**
 * Create an error MCP tool result
 */
export declare function errorResult(error: Error | string): MCPToolResult;
export declare const RESOURCE_LIMITS: {
    readonly MAX_VARIABLES: 10000;
    readonly MAX_ITERATIONS: 1000000;
    readonly MAX_MEMORY_BYTES: 4294967296;
    readonly MAX_CPU_TIME_MS: 600000;
    readonly MAX_CIRCUIT_DEPTH: 20;
    readonly MAX_QUBITS: 50;
    readonly PROGRESS_CHECK_INTERVAL_MS: 10000;
    readonly MIN_PROGRESS_THRESHOLD: 0.001;
};
export declare const ALLOWED_ORACLE_OPS: readonly ["==", "!=", "<", ">", "<=", ">=", "&&", "||", "!", "+", "-", "*", "/", "%", "."];
//# sourceMappingURL=types.d.ts.map