/**
 * Hyperbolic Reasoning Plugin - Type Definitions
 *
 * Types for hyperbolic geometry operations including Poincare ball embeddings,
 * taxonomic reasoning, hierarchy comparison, and entailment graphs.
 */
import { z } from 'zod';
/**
 * Point in hyperbolic space (Poincare ball model)
 */
export interface HyperbolicPoint {
    /** Coordinates in the Poincare ball (norm < 1) */
    readonly coordinates: Float32Array;
    /** Curvature parameter (negative) */
    readonly curvature: number;
    /** Dimension of the space */
    readonly dimension: number;
}
/**
 * Hyperbolic model type
 */
export type HyperbolicModel = 'poincare_ball' | 'lorentz' | 'klein' | 'half_plane';
/**
 * Mobius transformation parameters
 */
export interface MobiusTransform {
    /** Translation vector */
    readonly translation: Float32Array;
    /** Rotation matrix (flattened) */
    readonly rotation?: Float32Array;
    /** Scale factor */
    readonly scale: number;
}
/**
 * Node in a hierarchy
 */
export interface HierarchyNode {
    /** Unique node identifier */
    readonly id: string;
    /** Parent node ID (null for root) */
    readonly parent: string | null;
    /** Node features for embedding */
    readonly features?: Record<string, unknown>;
    /** Node label/name */
    readonly label?: string;
    /** Depth in tree (0 for root) */
    readonly depth?: number;
}
/**
 * Edge in a hierarchy (for DAGs)
 */
export interface HierarchyEdge {
    /** Source node ID */
    readonly source: string;
    /** Target node ID */
    readonly target: string;
    /** Edge weight */
    readonly weight?: number;
    /** Edge type */
    readonly type?: string;
}
/**
 * Complete hierarchy structure
 */
export interface Hierarchy {
    /** All nodes */
    readonly nodes: ReadonlyArray<HierarchyNode>;
    /** Optional edges (for DAGs) */
    readonly edges?: ReadonlyArray<HierarchyEdge>;
    /** Root node ID */
    readonly root?: string;
}
/**
 * Embedded hierarchy with hyperbolic coordinates
 */
export interface EmbeddedHierarchy {
    /** Node embeddings as id -> HyperbolicPoint */
    readonly embeddings: Map<string, HyperbolicPoint>;
    /** Model parameters */
    readonly model: HyperbolicModel;
    /** Learned or fixed curvature */
    readonly curvature: number;
    /** Embedding dimension */
    readonly dimension: number;
    /** Embedding quality metrics */
    readonly metrics: {
        readonly distortionMean: number;
        readonly distortionMax: number;
        readonly mapScore: number;
    };
}
/**
 * Taxonomic query type
 */
export type TaxonomicQueryType = 'is_a' | 'subsumption' | 'lowest_common_ancestor' | 'path' | 'similarity';
/**
 * Taxonomic query
 */
export interface TaxonomicQuery {
    /** Query type */
    readonly type: TaxonomicQueryType;
    /** Subject concept */
    readonly subject: string;
    /** Object concept (optional for some queries) */
    readonly object?: string;
}
/**
 * Inference configuration
 */
export interface InferenceConfig {
    /** Allow transitive reasoning */
    readonly transitive: boolean;
    /** Enable fuzzy matching */
    readonly fuzzy: boolean;
    /** Confidence threshold */
    readonly confidence: number;
}
/**
 * Taxonomic reasoning result
 */
export interface TaxonomicResult {
    /** Query result (boolean for is_a, etc.) */
    readonly result: boolean | string | string[] | number;
    /** Confidence in the result */
    readonly confidence: number;
    /** Explanation of reasoning path */
    readonly explanation: string;
    /** Intermediate steps if transitive */
    readonly steps?: ReadonlyArray<{
        readonly from: string;
        readonly to: string;
        readonly relation: string;
        readonly confidence: number;
    }>;
}
/**
 * Search mode for hierarchical search
 */
export type SearchMode = 'nearest' | 'subtree' | 'ancestors' | 'siblings' | 'cone';
/**
 * Search constraints
 */
export interface SearchConstraints {
    /** Maximum depth from root */
    readonly maxDepth?: number;
    /** Minimum depth from root */
    readonly minDepth?: number;
    /** Restrict to subtree of this node */
    readonly subtreeRoot?: string;
    /** Filter by node type */
    readonly nodeTypes?: ReadonlyArray<string>;
}
/**
 * Search result item
 */
export interface SearchResultItem {
    /** Node ID */
    readonly id: string;
    /** Hyperbolic distance */
    readonly distance: number;
    /** Euclidean similarity (for comparison) */
    readonly similarity?: number;
    /** Node metadata */
    readonly metadata?: Record<string, unknown>;
    /** Path from root */
    readonly path?: ReadonlyArray<string>;
}
/**
 * Search result
 */
export interface SearchResult {
    /** Matching items */
    readonly items: ReadonlyArray<SearchResultItem>;
    /** Total candidates considered */
    readonly totalCandidates: number;
    /** Search time in ms */
    readonly searchTimeMs: number;
}
/**
 * Alignment method for comparing hierarchies
 */
export type AlignmentMethod = 'wasserstein' | 'gromov_wasserstein' | 'tree_edit' | 'subtree_isomorphism';
/**
 * Comparison metric
 */
export type ComparisonMetric = 'structural_similarity' | 'semantic_similarity' | 'coverage' | 'precision';
/**
 * Node alignment pair
 */
export interface NodeAlignment {
    /** Source node ID */
    readonly source: string;
    /** Target node ID */
    readonly target: string;
    /** Alignment confidence */
    readonly confidence: number;
}
/**
 * Hierarchy comparison result
 */
export interface ComparisonResult {
    /** Overall similarity score (0-1) */
    readonly similarity: number;
    /** Node alignments */
    readonly alignments: ReadonlyArray<NodeAlignment>;
    /** Metrics */
    readonly metrics: Record<ComparisonMetric, number>;
    /** Unmatched source nodes */
    readonly unmatchedSource: ReadonlyArray<string>;
    /** Unmatched target nodes */
    readonly unmatchedTarget: ReadonlyArray<string>;
    /** Edit operations for tree edit distance */
    readonly editOperations?: ReadonlyArray<{
        readonly type: 'insert' | 'delete' | 'rename' | 'move';
        readonly node: string;
        readonly cost: number;
    }>;
}
/**
 * Concept for entailment graph
 */
export interface Concept {
    /** Unique concept ID */
    readonly id: string;
    /** Concept text/description */
    readonly text: string;
    /** Concept type/category */
    readonly type?: string;
    /** Pre-computed embedding */
    readonly embedding?: Float32Array;
}
/**
 * Entailment relation
 */
export interface EntailmentRelation {
    /** Premise concept ID */
    readonly premise: string;
    /** Hypothesis concept ID */
    readonly hypothesis: string;
    /** Entailment confidence */
    readonly confidence: number;
    /** Relation type */
    readonly type: 'entails' | 'contradicts' | 'neutral';
}
/**
 * Entailment graph action
 */
export type EntailmentAction = 'build' | 'query' | 'expand' | 'prune';
/**
 * Prune strategy
 */
export type PruneStrategy = 'none' | 'transitive_reduction' | 'confidence_threshold';
/**
 * Entailment graph
 */
export interface EntailmentGraph {
    /** All concepts */
    readonly concepts: ReadonlyArray<Concept>;
    /** Entailment relations */
    readonly relations: ReadonlyArray<EntailmentRelation>;
    /** Whether transitive closure is computed */
    readonly transitiveClosure: boolean;
    /** Graph statistics */
    readonly stats: {
        readonly nodeCount: number;
        readonly edgeCount: number;
        readonly density: number;
        readonly maxDepth: number;
    };
}
/**
 * Entailment query result
 */
export interface EntailmentQueryResult {
    /** Direct entailments */
    readonly direct: ReadonlyArray<EntailmentRelation>;
    /** Transitive entailments */
    readonly transitive?: ReadonlyArray<EntailmentRelation>;
    /** Contradiction paths */
    readonly contradictions?: ReadonlyArray<ReadonlyArray<string>>;
}
export declare const HierarchyNodeSchema: z.ZodObject<{
    id: z.ZodString;
    parent: z.ZodNullable<z.ZodString>;
    features: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    label: z.ZodOptional<z.ZodString>;
    depth: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    id: string;
    parent: string | null;
    features?: Record<string, unknown> | undefined;
    label?: string | undefined;
    depth?: number | undefined;
}, {
    id: string;
    parent: string | null;
    features?: Record<string, unknown> | undefined;
    label?: string | undefined;
    depth?: number | undefined;
}>;
export declare const HierarchyEdgeSchema: z.ZodObject<{
    source: z.ZodString;
    target: z.ZodString;
    weight: z.ZodOptional<z.ZodNumber>;
    type: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    source: string;
    target: string;
    type?: string | undefined;
    weight?: number | undefined;
}, {
    source: string;
    target: string;
    type?: string | undefined;
    weight?: number | undefined;
}>;
export declare const HierarchySchema: z.ZodObject<{
    nodes: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        parent: z.ZodNullable<z.ZodString>;
        features: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
        label: z.ZodOptional<z.ZodString>;
        depth: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        parent: string | null;
        features?: Record<string, unknown> | undefined;
        label?: string | undefined;
        depth?: number | undefined;
    }, {
        id: string;
        parent: string | null;
        features?: Record<string, unknown> | undefined;
        label?: string | undefined;
        depth?: number | undefined;
    }>, "many">;
    edges: z.ZodOptional<z.ZodArray<z.ZodObject<{
        source: z.ZodString;
        target: z.ZodString;
        weight: z.ZodOptional<z.ZodNumber>;
        type: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        source: string;
        target: string;
        type?: string | undefined;
        weight?: number | undefined;
    }, {
        source: string;
        target: string;
        type?: string | undefined;
        weight?: number | undefined;
    }>, "many">>;
    root: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    nodes: {
        id: string;
        parent: string | null;
        features?: Record<string, unknown> | undefined;
        label?: string | undefined;
        depth?: number | undefined;
    }[];
    edges?: {
        source: string;
        target: string;
        type?: string | undefined;
        weight?: number | undefined;
    }[] | undefined;
    root?: string | undefined;
}, {
    nodes: {
        id: string;
        parent: string | null;
        features?: Record<string, unknown> | undefined;
        label?: string | undefined;
        depth?: number | undefined;
    }[];
    edges?: {
        source: string;
        target: string;
        type?: string | undefined;
        weight?: number | undefined;
    }[] | undefined;
    root?: string | undefined;
}>;
export declare const EmbedHierarchyInputSchema: z.ZodObject<{
    hierarchy: z.ZodObject<{
        nodes: z.ZodArray<z.ZodObject<{
            id: z.ZodString;
            parent: z.ZodNullable<z.ZodString>;
            features: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
            label: z.ZodOptional<z.ZodString>;
            depth: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }, {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }>, "many">;
        edges: z.ZodOptional<z.ZodArray<z.ZodObject<{
            source: z.ZodString;
            target: z.ZodString;
            weight: z.ZodOptional<z.ZodNumber>;
            type: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }, {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }>, "many">>;
        root: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    }, {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    }>;
    model: z.ZodDefault<z.ZodEnum<["poincare_ball", "lorentz", "klein", "half_plane"]>>;
    parameters: z.ZodOptional<z.ZodObject<{
        dimensions: z.ZodDefault<z.ZodNumber>;
        curvature: z.ZodDefault<z.ZodNumber>;
        learnCurvature: z.ZodDefault<z.ZodBoolean>;
        epochs: z.ZodDefault<z.ZodNumber>;
        learningRate: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        dimensions: number;
        curvature: number;
        learnCurvature: boolean;
        epochs: number;
        learningRate: number;
    }, {
        dimensions?: number | undefined;
        curvature?: number | undefined;
        learnCurvature?: boolean | undefined;
        epochs?: number | undefined;
        learningRate?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    hierarchy: {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    };
    model: "poincare_ball" | "lorentz" | "klein" | "half_plane";
    parameters?: {
        dimensions: number;
        curvature: number;
        learnCurvature: boolean;
        epochs: number;
        learningRate: number;
    } | undefined;
}, {
    hierarchy: {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    };
    model?: "poincare_ball" | "lorentz" | "klein" | "half_plane" | undefined;
    parameters?: {
        dimensions?: number | undefined;
        curvature?: number | undefined;
        learnCurvature?: boolean | undefined;
        epochs?: number | undefined;
        learningRate?: number | undefined;
    } | undefined;
}>;
export type EmbedHierarchyInput = z.infer<typeof EmbedHierarchyInputSchema>;
export declare const TaxonomicReasonInputSchema: z.ZodObject<{
    query: z.ZodObject<{
        type: z.ZodEnum<["is_a", "subsumption", "lowest_common_ancestor", "path", "similarity"]>;
        subject: z.ZodString;
        object: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        type: "is_a" | "subsumption" | "lowest_common_ancestor" | "path" | "similarity";
        subject: string;
        object?: string | undefined;
    }, {
        type: "is_a" | "subsumption" | "lowest_common_ancestor" | "path" | "similarity";
        subject: string;
        object?: string | undefined;
    }>;
    taxonomy: z.ZodString;
    inference: z.ZodOptional<z.ZodObject<{
        transitive: z.ZodDefault<z.ZodBoolean>;
        fuzzy: z.ZodDefault<z.ZodBoolean>;
        confidence: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        transitive: boolean;
        fuzzy: boolean;
        confidence: number;
    }, {
        transitive?: boolean | undefined;
        fuzzy?: boolean | undefined;
        confidence?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    query: {
        type: "is_a" | "subsumption" | "lowest_common_ancestor" | "path" | "similarity";
        subject: string;
        object?: string | undefined;
    };
    taxonomy: string;
    inference?: {
        transitive: boolean;
        fuzzy: boolean;
        confidence: number;
    } | undefined;
}, {
    query: {
        type: "is_a" | "subsumption" | "lowest_common_ancestor" | "path" | "similarity";
        subject: string;
        object?: string | undefined;
    };
    taxonomy: string;
    inference?: {
        transitive?: boolean | undefined;
        fuzzy?: boolean | undefined;
        confidence?: number | undefined;
    } | undefined;
}>;
export type TaxonomicReasonInput = z.infer<typeof TaxonomicReasonInputSchema>;
export declare const SemanticSearchInputSchema: z.ZodObject<{
    query: z.ZodString;
    index: z.ZodString;
    searchMode: z.ZodDefault<z.ZodEnum<["nearest", "subtree", "ancestors", "siblings", "cone"]>>;
    constraints: z.ZodOptional<z.ZodObject<{
        maxDepth: z.ZodOptional<z.ZodNumber>;
        minDepth: z.ZodOptional<z.ZodNumber>;
        subtreeRoot: z.ZodOptional<z.ZodString>;
        nodeTypes: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        maxDepth?: number | undefined;
        minDepth?: number | undefined;
        subtreeRoot?: string | undefined;
        nodeTypes?: string[] | undefined;
    }, {
        maxDepth?: number | undefined;
        minDepth?: number | undefined;
        subtreeRoot?: string | undefined;
        nodeTypes?: string[] | undefined;
    }>>;
    topK: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    query: string;
    index: string;
    searchMode: "nearest" | "subtree" | "ancestors" | "siblings" | "cone";
    topK: number;
    constraints?: {
        maxDepth?: number | undefined;
        minDepth?: number | undefined;
        subtreeRoot?: string | undefined;
        nodeTypes?: string[] | undefined;
    } | undefined;
}, {
    query: string;
    index: string;
    searchMode?: "nearest" | "subtree" | "ancestors" | "siblings" | "cone" | undefined;
    constraints?: {
        maxDepth?: number | undefined;
        minDepth?: number | undefined;
        subtreeRoot?: string | undefined;
        nodeTypes?: string[] | undefined;
    } | undefined;
    topK?: number | undefined;
}>;
export type SemanticSearchInput = z.infer<typeof SemanticSearchInputSchema>;
export declare const HierarchyCompareInputSchema: z.ZodObject<{
    source: z.ZodObject<{
        nodes: z.ZodArray<z.ZodObject<{
            id: z.ZodString;
            parent: z.ZodNullable<z.ZodString>;
            features: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
            label: z.ZodOptional<z.ZodString>;
            depth: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }, {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }>, "many">;
        edges: z.ZodOptional<z.ZodArray<z.ZodObject<{
            source: z.ZodString;
            target: z.ZodString;
            weight: z.ZodOptional<z.ZodNumber>;
            type: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }, {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }>, "many">>;
        root: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    }, {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    }>;
    target: z.ZodObject<{
        nodes: z.ZodArray<z.ZodObject<{
            id: z.ZodString;
            parent: z.ZodNullable<z.ZodString>;
            features: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
            label: z.ZodOptional<z.ZodString>;
            depth: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }, {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }>, "many">;
        edges: z.ZodOptional<z.ZodArray<z.ZodObject<{
            source: z.ZodString;
            target: z.ZodString;
            weight: z.ZodOptional<z.ZodNumber>;
            type: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }, {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }>, "many">>;
        root: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    }, {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    }>;
    alignment: z.ZodDefault<z.ZodEnum<["wasserstein", "gromov_wasserstein", "tree_edit", "subtree_isomorphism"]>>;
    metrics: z.ZodOptional<z.ZodArray<z.ZodEnum<["structural_similarity", "semantic_similarity", "coverage", "precision"]>, "many">>;
}, "strip", z.ZodTypeAny, {
    source: {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    };
    target: {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    };
    alignment: "wasserstein" | "gromov_wasserstein" | "tree_edit" | "subtree_isomorphism";
    metrics?: ("structural_similarity" | "semantic_similarity" | "coverage" | "precision")[] | undefined;
}, {
    source: {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    };
    target: {
        nodes: {
            id: string;
            parent: string | null;
            features?: Record<string, unknown> | undefined;
            label?: string | undefined;
            depth?: number | undefined;
        }[];
        edges?: {
            source: string;
            target: string;
            type?: string | undefined;
            weight?: number | undefined;
        }[] | undefined;
        root?: string | undefined;
    };
    alignment?: "wasserstein" | "gromov_wasserstein" | "tree_edit" | "subtree_isomorphism" | undefined;
    metrics?: ("structural_similarity" | "semantic_similarity" | "coverage" | "precision")[] | undefined;
}>;
export type HierarchyCompareInput = z.infer<typeof HierarchyCompareInputSchema>;
export declare const ConceptSchema: z.ZodObject<{
    id: z.ZodString;
    text: z.ZodString;
    type: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    id: string;
    text: string;
    type?: string | undefined;
}, {
    id: string;
    text: string;
    type?: string | undefined;
}>;
export declare const EntailmentGraphInputSchema: z.ZodObject<{
    action: z.ZodEnum<["build", "query", "expand", "prune"]>;
    concepts: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        text: z.ZodString;
        type: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        text: string;
        type?: string | undefined;
    }, {
        id: string;
        text: string;
        type?: string | undefined;
    }>, "many">>;
    graphId: z.ZodOptional<z.ZodString>;
    query: z.ZodOptional<z.ZodObject<{
        premise: z.ZodOptional<z.ZodString>;
        hypothesis: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        premise?: string | undefined;
        hypothesis?: string | undefined;
    }, {
        premise?: string | undefined;
        hypothesis?: string | undefined;
    }>>;
    entailmentThreshold: z.ZodDefault<z.ZodNumber>;
    transitiveClosure: z.ZodDefault<z.ZodBoolean>;
    pruneStrategy: z.ZodOptional<z.ZodEnum<["none", "transitive_reduction", "confidence_threshold"]>>;
}, "strip", z.ZodTypeAny, {
    action: "build" | "query" | "expand" | "prune";
    entailmentThreshold: number;
    transitiveClosure: boolean;
    query?: {
        premise?: string | undefined;
        hypothesis?: string | undefined;
    } | undefined;
    concepts?: {
        id: string;
        text: string;
        type?: string | undefined;
    }[] | undefined;
    graphId?: string | undefined;
    pruneStrategy?: "none" | "transitive_reduction" | "confidence_threshold" | undefined;
}, {
    action: "build" | "query" | "expand" | "prune";
    query?: {
        premise?: string | undefined;
        hypothesis?: string | undefined;
    } | undefined;
    concepts?: {
        id: string;
        text: string;
        type?: string | undefined;
    }[] | undefined;
    graphId?: string | undefined;
    entailmentThreshold?: number | undefined;
    transitiveClosure?: boolean | undefined;
    pruneStrategy?: "none" | "transitive_reduction" | "confidence_threshold" | undefined;
}>;
export type EntailmentGraphInput = z.infer<typeof EntailmentGraphInputSchema>;
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
export interface HyperbolicReasoningConfig {
    embedding: {
        defaultDimensions: number;
        defaultCurvature: number;
        maxNodes: number;
    };
    search: {
        maxTopK: number;
        defaultTopK: number;
    };
    entailment: {
        defaultThreshold: number;
        maxConcepts: number;
    };
    resourceLimits: {
        maxMemoryBytes: number;
        maxCpuTimeMs: number;
        maxDepth: number;
    };
}
export interface HyperbolicReasoningBridge {
    initialized: boolean;
    initialize(): Promise<void>;
    dispose(): Promise<void>;
    embedHierarchy(hierarchy: Hierarchy, config: EmbedHierarchyInput['parameters']): Promise<EmbeddedHierarchy>;
    computeDistance(a: HyperbolicPoint, b: HyperbolicPoint): number;
    search(query: HyperbolicPoint, index: string, k: number): Promise<SearchResult>;
}
export interface ToolContext {
    bridge?: HyperbolicReasoningBridge;
    config?: HyperbolicReasoningConfig;
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
export declare const POINCARE_BALL_EPS = 1e-10;
export declare const MAX_NORM: number;
export declare const RESOURCE_LIMITS: {
    readonly MAX_NODES: 1000000;
    readonly MAX_EDGES: 10000000;
    readonly MAX_DIMENSIONS: 512;
    readonly MAX_DEPTH: 100;
    readonly MAX_BRANCHING: 10000;
    readonly MAX_MEMORY_BYTES: 2147483648;
    readonly MAX_CPU_TIME_MS: 300000;
};
/**
 * Clip vector to stay within Poincare ball
 */
export declare function clipToBall(vector: Float32Array, curvature: number): Float32Array;
/**
 * Compute hyperbolic distance in Poincare ball
 */
export declare function poincareDistance(x: Float32Array, y: Float32Array, c: number): number;
/**
 * Mobius addition in Poincare ball
 */
export declare function mobiusAdd(x: Float32Array, y: Float32Array, c: number): Float32Array;
/**
 * Exponential map from tangent space to Poincare ball
 */
export declare function expMap(v: Float32Array, c: number): Float32Array;
/**
 * Logarithmic map from Poincare ball to tangent space
 */
export declare function logMap(x: Float32Array, c: number): Float32Array;
//# sourceMappingURL=types.d.ts.map