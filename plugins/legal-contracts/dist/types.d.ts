/**
 * Legal Contracts Plugin - Type Definitions
 *
 * Core types for legal contract analysis including clause extraction,
 * risk assessment, contract comparison, obligation tracking, and playbook matching.
 *
 * Based on ADR-034: Legal Contract Analysis Plugin
 *
 * @module v3/plugins/legal-contracts/types
 */
import { z } from 'zod';
/**
 * Supported clause types for extraction
 */
export declare const ClauseType: z.ZodEnum<["indemnification", "limitation_of_liability", "termination", "confidentiality", "ip_assignment", "governing_law", "arbitration", "force_majeure", "warranty", "payment_terms", "non_compete", "non_solicitation", "assignment", "insurance", "representations", "covenants", "data_protection", "audit_rights"]>;
export type ClauseType = z.infer<typeof ClauseType>;
/**
 * Extracted clause with position and classification
 */
export interface ExtractedClause {
    /** Unique identifier for this clause */
    readonly id: string;
    /** Type of clause */
    readonly type: ClauseType;
    /** Raw text content of the clause */
    readonly text: string;
    /** Clause title or heading if present */
    readonly title?: string;
    /** Start position in document */
    readonly startOffset: number;
    /** End position in document */
    readonly endOffset: number;
    /** Section/article number if identifiable */
    readonly section?: string;
    /** Confidence score for classification (0-1) */
    readonly confidence: number;
    /** Sub-clauses or nested provisions */
    readonly subClauses?: ExtractedClause[];
    /** Key terms identified within clause */
    readonly keyTerms: string[];
    /** Semantic embedding vector for similarity matching */
    readonly embedding?: Float32Array;
}
/**
 * Result from clause extraction
 */
export interface ClauseExtractionResult {
    /** Success status */
    readonly success: boolean;
    /** Extracted clauses */
    readonly clauses: ExtractedClause[];
    /** Document metadata */
    readonly metadata: DocumentMetadata;
    /** Clauses that could not be classified */
    readonly unclassified: Array<{
        text: string;
        startOffset: number;
        endOffset: number;
        reason: string;
    }>;
    /** Execution time in ms */
    readonly durationMs: number;
}
/**
 * Party role in the contract
 */
export declare const PartyRole: z.ZodEnum<["buyer", "seller", "licensor", "licensee", "employer", "employee", "landlord", "tenant", "lender", "borrower", "service_provider", "client"]>;
export type PartyRole = z.infer<typeof PartyRole>;
/**
 * Risk categories for assessment
 */
export declare const RiskCategory: z.ZodEnum<["financial", "operational", "legal", "reputational", "compliance", "strategic", "security", "performance"]>;
export type RiskCategory = z.infer<typeof RiskCategory>;
/**
 * Risk severity levels
 */
export declare const RiskSeverity: z.ZodEnum<["low", "medium", "high", "critical"]>;
export type RiskSeverity = z.infer<typeof RiskSeverity>;
/**
 * Individual risk finding
 */
export interface RiskFinding {
    /** Unique identifier */
    readonly id: string;
    /** Risk category */
    readonly category: RiskCategory;
    /** Severity level */
    readonly severity: RiskSeverity;
    /** Risk title/summary */
    readonly title: string;
    /** Detailed description */
    readonly description: string;
    /** Associated clause(s) */
    readonly clauseIds: string[];
    /** Potential financial impact range */
    readonly financialImpact?: {
        min: number;
        max: number;
        currency: string;
        probability: number;
    };
    /** Suggested mitigation strategies */
    readonly mitigations: string[];
    /** Legal precedent or standard deviation flag */
    readonly deviatesFromStandard: boolean;
    /** Confidence in assessment (0-1) */
    readonly confidence: number;
    /** Jurisdiction-specific notes */
    readonly jurisdictionNotes?: string;
}
/**
 * Overall risk assessment result
 */
export interface RiskAssessmentResult {
    /** Success status */
    readonly success: boolean;
    /** Party role perspective used */
    readonly partyRole: PartyRole;
    /** All risk findings */
    readonly risks: RiskFinding[];
    /** Summary by category */
    readonly categorySummary: Record<RiskCategory, {
        count: number;
        highestSeverity: RiskSeverity;
        averageScore: number;
    }>;
    /** Overall risk score (0-100) */
    readonly overallScore: number;
    /** Risk grade (A-F) */
    readonly grade: 'A' | 'B' | 'C' | 'D' | 'F';
    /** Top 5 most critical risks */
    readonly criticalRisks: RiskFinding[];
    /** Execution time in ms */
    readonly durationMs: number;
}
/**
 * Comparison mode for contract analysis
 */
export declare const ComparisonMode: z.ZodEnum<["structural", "semantic", "full"]>;
export type ComparisonMode = z.infer<typeof ComparisonMode>;
/**
 * Type of change detected
 */
export type ChangeType = 'added' | 'removed' | 'modified' | 'moved' | 'unchanged';
/**
 * Individual change between contracts
 */
export interface ContractChange {
    /** Change type */
    readonly type: ChangeType;
    /** Clause type affected */
    readonly clauseType?: ClauseType;
    /** Section in base document */
    readonly baseSection?: string;
    /** Section in compare document */
    readonly compareSection?: string;
    /** Original text */
    readonly baseText?: string;
    /** New/changed text */
    readonly compareText?: string;
    /** Significance score (0-1) */
    readonly significance: number;
    /** Impact assessment */
    readonly impact: 'favorable' | 'unfavorable' | 'neutral' | 'requires_review';
    /** Detailed explanation of change */
    readonly explanation: string;
    /** Suggested action */
    readonly suggestedAction?: string;
}
/**
 * Semantic alignment between clauses
 */
export interface ClauseAlignment {
    /** Base document clause ID */
    readonly baseClauseId: string;
    /** Compare document clause ID */
    readonly compareClauseId: string;
    /** Similarity score (0-1) */
    readonly similarity: number;
    /** Alignment type */
    readonly alignmentType: 'exact' | 'similar' | 'related' | 'no_match';
    /** Key differences */
    readonly differences: string[];
}
/**
 * Contract comparison result
 */
export interface ContractComparisonResult {
    /** Success status */
    readonly success: boolean;
    /** Comparison mode used */
    readonly mode: ComparisonMode;
    /** All detected changes */
    readonly changes: ContractChange[];
    /** Clause alignments */
    readonly alignments: ClauseAlignment[];
    /** Overall similarity score (0-1) */
    readonly similarityScore: number;
    /** Summary statistics */
    readonly summary: {
        totalChanges: number;
        added: number;
        removed: number;
        modified: number;
        favorable: number;
        unfavorable: number;
    };
    /** Redline markup if requested */
    readonly redlineMarkup?: string;
    /** Execution time in ms */
    readonly durationMs: number;
}
/**
 * Obligation types
 */
export declare const ObligationType: z.ZodEnum<["payment", "delivery", "notification", "approval", "compliance", "reporting", "confidentiality", "performance", "insurance", "renewal", "termination"]>;
export type ObligationType = z.infer<typeof ObligationType>;
/**
 * Obligation status
 */
export type ObligationStatus = 'pending' | 'in_progress' | 'completed' | 'overdue' | 'waived';
/**
 * Extracted obligation
 */
export interface Obligation {
    /** Unique identifier */
    readonly id: string;
    /** Obligation type */
    readonly type: ObligationType;
    /** Responsible party */
    readonly party: string;
    /** Obligation description */
    readonly description: string;
    /** Due date if applicable */
    readonly dueDate?: Date;
    /** Deadline type */
    readonly deadlineType?: 'hard' | 'soft' | 'recurring';
    /** Recurrence pattern (ISO 8601 duration) */
    readonly recurrence?: string;
    /** Triggering condition */
    readonly triggerCondition?: string;
    /** Dependencies (other obligation IDs) */
    readonly dependsOn: string[];
    /** Obligations blocked by this one */
    readonly blocks: string[];
    /** Associated clause IDs */
    readonly clauseIds: string[];
    /** Monetary value if applicable */
    readonly monetaryValue?: {
        amount: number;
        currency: string;
    };
    /** Penalty for non-compliance */
    readonly penalty?: string;
    /** Current status */
    readonly status: ObligationStatus;
    /** Priority level */
    readonly priority: 'low' | 'medium' | 'high' | 'critical';
}
/**
 * Obligation dependency graph node
 */
export interface ObligationNode {
    /** Obligation */
    readonly obligation: Obligation;
    /** Incoming edges (dependencies) */
    readonly dependencies: string[];
    /** Outgoing edges (dependents) */
    readonly dependents: string[];
    /** Critical path flag */
    readonly onCriticalPath: boolean;
    /** Earliest start date */
    readonly earliestStart?: Date;
    /** Latest finish date */
    readonly latestFinish?: Date;
    /** Float/slack time in days */
    readonly floatDays?: number;
}
/**
 * Obligation tracking result
 */
export interface ObligationTrackingResult {
    /** Success status */
    readonly success: boolean;
    /** All obligations */
    readonly obligations: Obligation[];
    /** Dependency graph */
    readonly graph: {
        nodes: ObligationNode[];
        edges: Array<{
            from: string;
            to: string;
            type: 'depends_on' | 'blocks' | 'triggers';
        }>;
    };
    /** Timeline view */
    readonly timeline: Array<{
        date: Date;
        obligations: string[];
        isMilestone: boolean;
    }>;
    /** Upcoming deadlines (next 30 days) */
    readonly upcomingDeadlines: Obligation[];
    /** Overdue obligations */
    readonly overdue: Obligation[];
    /** Execution time in ms */
    readonly durationMs: number;
}
/**
 * Strictness level for playbook matching
 */
export declare const PlaybookStrictness: z.ZodEnum<["strict", "moderate", "flexible"]>;
export type PlaybookStrictness = z.infer<typeof PlaybookStrictness>;
/**
 * Playbook position for a clause type
 */
export interface PlaybookPosition {
    /** Clause type */
    readonly clauseType: ClauseType;
    /** Preferred language/position */
    readonly preferredLanguage: string;
    /** Acceptable variations */
    readonly acceptableVariations: string[];
    /** Red lines (non-negotiable) */
    readonly redLines: string[];
    /** Fallback positions in order of preference */
    readonly fallbackPositions: Array<{
        language: string;
        priority: number;
        conditions?: string;
    }>;
    /** Negotiation notes */
    readonly negotiationNotes: string;
    /** Business justification */
    readonly businessJustification: string;
}
/**
 * Complete playbook
 */
export interface Playbook {
    /** Playbook identifier */
    readonly id: string;
    /** Playbook name */
    readonly name: string;
    /** Contract type this applies to */
    readonly contractType: string;
    /** Jurisdiction */
    readonly jurisdiction: string;
    /** Party role perspective */
    readonly partyRole: PartyRole;
    /** Last updated */
    readonly updatedAt: Date;
    /** Version */
    readonly version: string;
    /** Positions by clause type */
    readonly positions: PlaybookPosition[];
}
/**
 * Match result for a single clause
 */
export interface PlaybookMatch {
    /** Clause from document */
    readonly clauseId: string;
    /** Matching playbook position */
    readonly position: PlaybookPosition;
    /** Match status */
    readonly status: 'matches_preferred' | 'matches_acceptable' | 'requires_fallback' | 'violates_redline' | 'no_match';
    /** Similarity to preferred position (0-1) */
    readonly preferredSimilarity: number;
    /** Best matching fallback if applicable */
    readonly matchedFallback?: {
        language: string;
        priority: number;
        similarity: number;
    };
    /** Suggested alternative language */
    readonly suggestedAlternative?: string;
    /** Negotiation recommendation */
    readonly recommendation: string;
    /** Risk if current language accepted */
    readonly riskIfAccepted?: string;
}
/**
 * Playbook matching result
 */
export interface PlaybookMatchResult {
    /** Success status */
    readonly success: boolean;
    /** Playbook used */
    readonly playbook: {
        id: string;
        name: string;
        version: string;
    };
    /** Match results per clause */
    readonly matches: PlaybookMatch[];
    /** Summary */
    readonly summary: {
        totalClauses: number;
        matchesPreferred: number;
        matchesAcceptable: number;
        requiresFallback: number;
        violatesRedline: number;
        noMatch: number;
    };
    /** Red line violations requiring attention */
    readonly redLineViolations: PlaybookMatch[];
    /** Negotiation priorities (ordered) */
    readonly negotiationPriorities: Array<{
        clauseId: string;
        priority: number;
        reason: string;
    }>;
    /** Execution time in ms */
    readonly durationMs: number;
}
/**
 * Document metadata
 */
export interface DocumentMetadata {
    /** Document identifier */
    readonly id: string;
    /** Document title */
    readonly title?: string;
    /** Document format */
    readonly format: 'pdf' | 'docx' | 'txt' | 'html';
    /** Total pages */
    readonly pages?: number;
    /** Total words */
    readonly wordCount: number;
    /** Total characters */
    readonly charCount: number;
    /** Detected language */
    readonly language: string;
    /** Contract type if identified */
    readonly contractType?: string;
    /** Effective date if found */
    readonly effectiveDate?: Date;
    /** Expiration date if found */
    readonly expirationDate?: Date;
    /** Parties identified */
    readonly parties: Array<{
        name: string;
        role?: PartyRole;
        address?: string;
    }>;
    /** Governing law jurisdiction */
    readonly governingLaw?: string;
    /** Document hash for integrity */
    readonly contentHash: string;
}
/**
 * Matter isolation context
 */
export interface MatterContext {
    /** Unique matter identifier */
    readonly matterId: string;
    /** Client identifier */
    readonly clientId: string;
    /** Authorized users */
    readonly authorizedUsers: string[];
    /** Ethical wall restrictions */
    readonly ethicalWalls?: string[];
    /** Audit log reference */
    readonly auditLogId: string;
}
/**
 * User role for access control
 */
export declare const UserRole: z.ZodEnum<["partner", "associate", "paralegal", "contract_manager", "client"]>;
export type UserRole = z.infer<typeof UserRole>;
/**
 * Tool access permissions by role
 */
export declare const RolePermissions: Record<UserRole, string[]>;
/**
 * Audit log entry
 */
export interface AuditLogEntry {
    /** Timestamp (ISO 8601) */
    readonly timestamp: string;
    /** User ID */
    readonly userId: string;
    /** User role at time of access */
    readonly userRole: UserRole;
    /** Matter ID */
    readonly matterId: string;
    /** Tool invoked */
    readonly toolName: string;
    /** Document hash (not content) */
    readonly documentHash: string;
    /** Operation type */
    readonly operationType: 'analyze' | 'compare' | 'export';
    /** High-level result (no privileged content) */
    readonly resultSummary: string;
    /** Optional billing reference */
    readonly billingCode?: string;
}
/**
 * Input schema for legal/clause-extract
 */
export declare const ClauseExtractInputSchema: z.ZodObject<{
    document: z.ZodString;
    clauseTypes: z.ZodOptional<z.ZodArray<z.ZodEnum<["indemnification", "limitation_of_liability", "termination", "confidentiality", "ip_assignment", "governing_law", "arbitration", "force_majeure", "warranty", "payment_terms", "non_compete", "non_solicitation", "assignment", "insurance", "representations", "covenants", "data_protection", "audit_rights"]>, "many">>;
    jurisdiction: z.ZodDefault<z.ZodString>;
    includePositions: z.ZodDefault<z.ZodBoolean>;
    includeEmbeddings: z.ZodDefault<z.ZodBoolean>;
    matterContext: z.ZodOptional<z.ZodObject<{
        matterId: z.ZodString;
        clientId: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        matterId: string;
        clientId: string;
    }, {
        matterId: string;
        clientId: string;
    }>>;
}, "strip", z.ZodTypeAny, {
    document: string;
    jurisdiction: string;
    includePositions: boolean;
    includeEmbeddings: boolean;
    clauseTypes?: ("indemnification" | "limitation_of_liability" | "termination" | "confidentiality" | "ip_assignment" | "governing_law" | "arbitration" | "force_majeure" | "warranty" | "payment_terms" | "non_compete" | "non_solicitation" | "assignment" | "insurance" | "representations" | "covenants" | "data_protection" | "audit_rights")[] | undefined;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
}, {
    document: string;
    clauseTypes?: ("indemnification" | "limitation_of_liability" | "termination" | "confidentiality" | "ip_assignment" | "governing_law" | "arbitration" | "force_majeure" | "warranty" | "payment_terms" | "non_compete" | "non_solicitation" | "assignment" | "insurance" | "representations" | "covenants" | "data_protection" | "audit_rights")[] | undefined;
    jurisdiction?: string | undefined;
    includePositions?: boolean | undefined;
    includeEmbeddings?: boolean | undefined;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
}>;
export type ClauseExtractInput = z.infer<typeof ClauseExtractInputSchema>;
/**
 * Input schema for legal/risk-assess
 */
export declare const RiskAssessInputSchema: z.ZodObject<{
    document: z.ZodString;
    partyRole: z.ZodEnum<["buyer", "seller", "licensor", "licensee", "employer", "employee", "landlord", "tenant", "lender", "borrower", "service_provider", "client"]>;
    riskCategories: z.ZodOptional<z.ZodArray<z.ZodEnum<["financial", "operational", "legal", "reputational", "compliance", "strategic", "security", "performance"]>, "many">>;
    industryContext: z.ZodOptional<z.ZodString>;
    threshold: z.ZodOptional<z.ZodEnum<["low", "medium", "high", "critical"]>>;
    includeFinancialImpact: z.ZodDefault<z.ZodBoolean>;
    matterContext: z.ZodOptional<z.ZodObject<{
        matterId: z.ZodString;
        clientId: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        matterId: string;
        clientId: string;
    }, {
        matterId: string;
        clientId: string;
    }>>;
}, "strip", z.ZodTypeAny, {
    document: string;
    partyRole: "buyer" | "seller" | "licensor" | "licensee" | "employer" | "employee" | "landlord" | "tenant" | "lender" | "borrower" | "service_provider" | "client";
    includeFinancialImpact: boolean;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    riskCategories?: ("financial" | "operational" | "legal" | "reputational" | "compliance" | "strategic" | "security" | "performance")[] | undefined;
    industryContext?: string | undefined;
    threshold?: "low" | "medium" | "high" | "critical" | undefined;
}, {
    document: string;
    partyRole: "buyer" | "seller" | "licensor" | "licensee" | "employer" | "employee" | "landlord" | "tenant" | "lender" | "borrower" | "service_provider" | "client";
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    riskCategories?: ("financial" | "operational" | "legal" | "reputational" | "compliance" | "strategic" | "security" | "performance")[] | undefined;
    industryContext?: string | undefined;
    threshold?: "low" | "medium" | "high" | "critical" | undefined;
    includeFinancialImpact?: boolean | undefined;
}>;
export type RiskAssessInput = z.infer<typeof RiskAssessInputSchema>;
/**
 * Input schema for legal/contract-compare
 */
export declare const ContractCompareInputSchema: z.ZodObject<{
    baseDocument: z.ZodString;
    compareDocument: z.ZodString;
    comparisonMode: z.ZodDefault<z.ZodEnum<["structural", "semantic", "full"]>>;
    highlightChanges: z.ZodDefault<z.ZodBoolean>;
    generateRedline: z.ZodDefault<z.ZodBoolean>;
    focusClauseTypes: z.ZodOptional<z.ZodArray<z.ZodEnum<["indemnification", "limitation_of_liability", "termination", "confidentiality", "ip_assignment", "governing_law", "arbitration", "force_majeure", "warranty", "payment_terms", "non_compete", "non_solicitation", "assignment", "insurance", "representations", "covenants", "data_protection", "audit_rights"]>, "many">>;
    matterContext: z.ZodOptional<z.ZodObject<{
        matterId: z.ZodString;
        clientId: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        matterId: string;
        clientId: string;
    }, {
        matterId: string;
        clientId: string;
    }>>;
}, "strip", z.ZodTypeAny, {
    baseDocument: string;
    compareDocument: string;
    comparisonMode: "structural" | "semantic" | "full";
    highlightChanges: boolean;
    generateRedline: boolean;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    focusClauseTypes?: ("indemnification" | "limitation_of_liability" | "termination" | "confidentiality" | "ip_assignment" | "governing_law" | "arbitration" | "force_majeure" | "warranty" | "payment_terms" | "non_compete" | "non_solicitation" | "assignment" | "insurance" | "representations" | "covenants" | "data_protection" | "audit_rights")[] | undefined;
}, {
    baseDocument: string;
    compareDocument: string;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    comparisonMode?: "structural" | "semantic" | "full" | undefined;
    highlightChanges?: boolean | undefined;
    generateRedline?: boolean | undefined;
    focusClauseTypes?: ("indemnification" | "limitation_of_liability" | "termination" | "confidentiality" | "ip_assignment" | "governing_law" | "arbitration" | "force_majeure" | "warranty" | "payment_terms" | "non_compete" | "non_solicitation" | "assignment" | "insurance" | "representations" | "covenants" | "data_protection" | "audit_rights")[] | undefined;
}>;
export type ContractCompareInput = z.infer<typeof ContractCompareInputSchema>;
/**
 * Input schema for legal/obligation-track
 */
export declare const ObligationTrackInputSchema: z.ZodObject<{
    document: z.ZodString;
    party: z.ZodOptional<z.ZodString>;
    timeframe: z.ZodOptional<z.ZodString>;
    obligationTypes: z.ZodOptional<z.ZodArray<z.ZodEnum<["payment", "delivery", "notification", "approval", "compliance", "reporting", "confidentiality", "performance", "insurance", "renewal", "termination"]>, "many">>;
    includeDependencies: z.ZodDefault<z.ZodBoolean>;
    includeTimeline: z.ZodDefault<z.ZodBoolean>;
    matterContext: z.ZodOptional<z.ZodObject<{
        matterId: z.ZodString;
        clientId: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        matterId: string;
        clientId: string;
    }, {
        matterId: string;
        clientId: string;
    }>>;
}, "strip", z.ZodTypeAny, {
    document: string;
    includeDependencies: boolean;
    includeTimeline: boolean;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    party?: string | undefined;
    timeframe?: string | undefined;
    obligationTypes?: ("termination" | "confidentiality" | "insurance" | "compliance" | "performance" | "payment" | "delivery" | "notification" | "approval" | "reporting" | "renewal")[] | undefined;
}, {
    document: string;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    party?: string | undefined;
    timeframe?: string | undefined;
    obligationTypes?: ("termination" | "confidentiality" | "insurance" | "compliance" | "performance" | "payment" | "delivery" | "notification" | "approval" | "reporting" | "renewal")[] | undefined;
    includeDependencies?: boolean | undefined;
    includeTimeline?: boolean | undefined;
}>;
export type ObligationTrackInput = z.infer<typeof ObligationTrackInputSchema>;
/**
 * Input schema for legal/playbook-match
 */
export declare const PlaybookMatchInputSchema: z.ZodObject<{
    document: z.ZodString;
    playbook: z.ZodString;
    strictness: z.ZodDefault<z.ZodEnum<["strict", "moderate", "flexible"]>>;
    suggestAlternatives: z.ZodDefault<z.ZodBoolean>;
    prioritizeClauses: z.ZodOptional<z.ZodArray<z.ZodEnum<["indemnification", "limitation_of_liability", "termination", "confidentiality", "ip_assignment", "governing_law", "arbitration", "force_majeure", "warranty", "payment_terms", "non_compete", "non_solicitation", "assignment", "insurance", "representations", "covenants", "data_protection", "audit_rights"]>, "many">>;
    matterContext: z.ZodOptional<z.ZodObject<{
        matterId: z.ZodString;
        clientId: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        matterId: string;
        clientId: string;
    }, {
        matterId: string;
        clientId: string;
    }>>;
}, "strip", z.ZodTypeAny, {
    document: string;
    playbook: string;
    strictness: "strict" | "moderate" | "flexible";
    suggestAlternatives: boolean;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    prioritizeClauses?: ("indemnification" | "limitation_of_liability" | "termination" | "confidentiality" | "ip_assignment" | "governing_law" | "arbitration" | "force_majeure" | "warranty" | "payment_terms" | "non_compete" | "non_solicitation" | "assignment" | "insurance" | "representations" | "covenants" | "data_protection" | "audit_rights")[] | undefined;
}, {
    document: string;
    playbook: string;
    matterContext?: {
        matterId: string;
        clientId: string;
    } | undefined;
    strictness?: "strict" | "moderate" | "flexible" | undefined;
    suggestAlternatives?: boolean | undefined;
    prioritizeClauses?: ("indemnification" | "limitation_of_liability" | "termination" | "confidentiality" | "ip_assignment" | "governing_law" | "arbitration" | "force_majeure" | "warranty" | "payment_terms" | "non_compete" | "non_solicitation" | "assignment" | "insurance" | "representations" | "covenants" | "data_protection" | "audit_rights")[] | undefined;
}>;
export type PlaybookMatchInput = z.infer<typeof PlaybookMatchInputSchema>;
/**
 * Flash Attention Bridge for clause analysis
 */
export interface IAttentionBridge {
    /**
     * Compute cross-attention between clause embeddings for similarity
     */
    computeCrossAttention(queryEmbeddings: Float32Array[], keyEmbeddings: Float32Array[], mask?: boolean[][]): Promise<Float32Array[][]>;
    /**
     * Align clauses between two documents using attention
     */
    alignClauses(baseClauses: ExtractedClause[], compareClauses: ExtractedClause[]): Promise<ClauseAlignment[]>;
    /**
     * Find most relevant clauses for a given query
     */
    findRelevantClauses(query: string | Float32Array, clauses: ExtractedClause[], topK: number): Promise<Array<{
        clause: ExtractedClause;
        score: number;
    }>>;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
}
/**
 * DAG Bridge for obligation tracking
 */
export interface IDAGBridge {
    /**
     * Build obligation dependency graph
     */
    buildDependencyGraph(obligations: Obligation[]): Promise<ObligationTrackingResult['graph']>;
    /**
     * Find critical path through obligations
     */
    findCriticalPath(graph: ObligationTrackingResult['graph']): Promise<string[]>;
    /**
     * Perform topological sort of obligations
     */
    topologicalSort(obligations: Obligation[]): Promise<Obligation[]>;
    /**
     * Detect cycles in dependency graph
     */
    detectCycles(graph: ObligationTrackingResult['graph']): Promise<string[][]>;
    /**
     * Calculate slack/float for each obligation
     */
    calculateFloat(graph: ObligationTrackingResult['graph'], projectEnd: Date): Promise<Map<string, number>>;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
}
/**
 * Plugin configuration
 */
export interface LegalContractsConfig {
    /** Clause extraction settings */
    extraction: {
        /** Minimum confidence for clause classification */
        minConfidence: number;
        /** Include semantic embeddings */
        includeEmbeddings: boolean;
        /** Embedding dimension */
        embeddingDimension: number;
    };
    /** Risk assessment settings */
    risk: {
        /** Default risk threshold */
        defaultThreshold: RiskSeverity;
        /** Include financial impact estimates */
        includeFinancialImpact: boolean;
    };
    /** Comparison settings */
    comparison: {
        /** Similarity threshold for clause alignment */
        similarityThreshold: number;
        /** Include redline generation */
        generateRedline: boolean;
    };
    /** Security settings */
    security: {
        /** Enable matter isolation */
        matterIsolation: boolean;
        /** Audit logging level */
        auditLevel: 'minimal' | 'standard' | 'comprehensive';
        /** Allowed document root for file inputs */
        allowedDocumentRoot: string;
    };
}
/**
 * Default configuration
 */
export declare const DEFAULT_CONFIG: LegalContractsConfig;
/**
 * Legal contracts plugin error codes
 */
export declare const LegalErrorCodes: {
    readonly DOCUMENT_TOO_LARGE: "LEGAL_DOCUMENT_TOO_LARGE";
    readonly INVALID_DOCUMENT_FORMAT: "LEGAL_INVALID_DOCUMENT_FORMAT";
    readonly CLAUSE_EXTRACTION_FAILED: "LEGAL_CLAUSE_EXTRACTION_FAILED";
    readonly RISK_ASSESSMENT_FAILED: "LEGAL_RISK_ASSESSMENT_FAILED";
    readonly COMPARISON_FAILED: "LEGAL_COMPARISON_FAILED";
    readonly OBLIGATION_PARSING_FAILED: "LEGAL_OBLIGATION_PARSING_FAILED";
    readonly PLAYBOOK_INVALID: "LEGAL_PLAYBOOK_INVALID";
    readonly MATTER_ACCESS_DENIED: "LEGAL_MATTER_ACCESS_DENIED";
    readonly ETHICAL_WALL_VIOLATION: "LEGAL_ETHICAL_WALL_VIOLATION";
    readonly WASM_NOT_INITIALIZED: "LEGAL_WASM_NOT_INITIALIZED";
    readonly PRIVILEGE_VIOLATION: "LEGAL_PRIVILEGE_VIOLATION";
};
export type LegalErrorCode = (typeof LegalErrorCodes)[keyof typeof LegalErrorCodes];
/**
 * Legal contracts plugin error
 */
export declare class LegalContractsError extends Error {
    readonly code: LegalErrorCode;
    readonly details?: Record<string, unknown>;
    constructor(code: LegalErrorCode, message: string, details?: Record<string, unknown>);
}
//# sourceMappingURL=types.d.ts.map