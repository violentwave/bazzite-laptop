/**
 * Healthcare Clinical Plugin - Type Definitions
 *
 * Core types for HIPAA-compliant clinical decision support including
 * patient similarity, drug interactions, clinical pathways, literature search,
 * and medical ontology navigation.
 */
import { z } from 'zod';
/**
 * MCP Tool definition
 */
export interface MCPTool {
    name: string;
    description: string;
    category: string;
    version: string;
    tags: string[];
    cacheable: boolean;
    cacheTTL: number;
    inputSchema: {
        type: 'object';
        properties: Record<string, unknown>;
        required: string[];
    };
    handler: (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>;
}
/**
 * MCP Tool result
 */
export interface MCPToolResult {
    success: boolean;
    data?: unknown;
    error?: string;
    metadata?: {
        durationMs?: number;
        cached?: boolean;
        wasmUsed?: boolean;
    };
}
/**
 * Tool execution context
 */
export interface ToolContext {
    logger?: Logger;
    config?: HealthcareConfig;
    bridge?: HealthcareBridge;
    userId?: string;
    userRoles?: HealthcareRole[];
    auditLogger?: AuditLogger;
}
/**
 * Simple logger interface
 */
export interface Logger {
    debug: (msg: string, meta?: Record<string, unknown>) => void;
    info: (msg: string, meta?: Record<string, unknown>) => void;
    warn: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
}
/**
 * Patient clinical features for similarity matching
 */
export interface PatientFeatures {
    diagnoses: string[];
    labResults?: Record<string, number>;
    vitals?: Record<string, number>;
    medications?: string[];
    demographics?: PatientDemographics;
    procedures?: string[];
    allergies?: string[];
}
/**
 * Patient demographics (anonymized)
 */
export interface PatientDemographics {
    ageRange?: string;
    gender?: string;
    ethnicity?: string;
}
/**
 * Similar patient result
 */
export interface SimilarPatient {
    patientId: string;
    similarity: number;
    matchingDiagnoses: string[];
    matchingMedications: string[];
    treatmentOutcome?: string;
    embedding?: Float32Array;
}
/**
 * Patient similarity search result
 */
export interface PatientSimilarityResult {
    query: PatientFeatures;
    similarPatients: SimilarPatient[];
    searchTime: number;
    cohortSize: number;
    confidence: number;
}
/**
 * Drug interaction severity levels
 */
export type InteractionSeverity = 'major' | 'moderate' | 'minor' | 'contraindicated';
/**
 * Drug-drug interaction
 */
export interface DrugInteraction {
    drug1: string;
    drug2: string;
    severity: InteractionSeverity;
    description: string;
    mechanism?: string;
    clinicalEffect?: string;
    management?: string;
    references?: string[];
}
/**
 * Drug-condition interaction
 */
export interface DrugConditionInteraction {
    drug: string;
    condition: string;
    severity: InteractionSeverity;
    description: string;
    recommendation?: string;
}
/**
 * Drug interactions analysis result
 */
export interface DrugInteractionsResult {
    medications: string[];
    drugDrugInteractions: DrugInteraction[];
    drugConditionInteractions: DrugConditionInteraction[];
    riskScore: number;
    recommendations: string[];
    analysisTime: number;
}
/**
 * Clinical pathway step
 */
export interface PathwayStep {
    id: string;
    name: string;
    description: string;
    type: 'assessment' | 'intervention' | 'monitoring' | 'decision' | 'outcome';
    timing?: string;
    responsible?: string;
    prerequisites?: string[];
    outcomes?: string[];
}
/**
 * Clinical pathway
 */
export interface ClinicalPathway {
    id: string;
    name: string;
    diagnosis: string;
    version: string;
    steps: PathwayStep[];
    expectedDuration?: string;
    evidenceLevel?: EvidenceLevel;
    source?: string;
    lastUpdated?: string;
}
/**
 * Pathway constraints
 */
export interface PathwayConstraints {
    excludeMedications?: string[];
    costSensitive?: boolean;
    outpatientOnly?: boolean;
    ageRestrictions?: string;
    comorbidityConsiderations?: string[];
}
/**
 * Clinical pathway recommendation result
 */
export interface ClinicalPathwayResult {
    primaryDiagnosis: string;
    recommendedPathways: ClinicalPathway[];
    alternativePathways: ClinicalPathway[];
    contraindicated: string[];
    constraints: PathwayConstraints;
    confidence: number;
    analysisTime: number;
}
/**
 * Evidence level for medical literature
 */
export type EvidenceLevel = 'systematic-review' | 'rct' | 'cohort' | 'case-control' | 'case-series' | 'expert-opinion' | 'any';
/**
 * Literature source
 */
export type LiteratureSource = 'pubmed' | 'cochrane' | 'uptodate' | 'local';
/**
 * Literature search result
 */
export interface LiteratureArticle {
    id: string;
    title: string;
    authors: string[];
    abstract?: string;
    source: LiteratureSource;
    publicationDate?: string;
    evidenceLevel?: EvidenceLevel;
    relevanceScore: number;
    doi?: string;
    pmid?: string;
    meshTerms?: string[];
}
/**
 * Literature search result
 */
export interface LiteratureSearchResult {
    query: string;
    articles: LiteratureArticle[];
    totalResults: number;
    searchTime: number;
    sources: LiteratureSource[];
    filters: {
        dateRange?: {
            from?: string;
            to?: string;
        };
        evidenceLevel?: EvidenceLevel;
    };
}
/**
 * Medical ontology types
 */
export type MedicalOntology = 'icd10' | 'snomed' | 'loinc' | 'rxnorm';
/**
 * Navigation direction in ontology
 */
export type OntologyDirection = 'ancestors' | 'descendants' | 'siblings' | 'related';
/**
 * Ontology node
 */
export interface OntologyNode {
    code: string;
    display: string;
    ontology: MedicalOntology;
    definition?: string;
    synonyms?: string[];
    parentCodes?: string[];
    childCodes?: string[];
    depth?: number;
}
/**
 * Ontology navigation result
 */
export interface OntologyNavigationResult {
    sourceCode: string;
    sourceNode: OntologyNode;
    direction: OntologyDirection;
    results: OntologyNode[];
    depth: number;
    totalNodes: number;
    navigationTime: number;
}
/**
 * Healthcare roles for RBAC
 */
export type HealthcareRole = 'PHYSICIAN' | 'NURSE' | 'PHARMACIST' | 'RESEARCHER' | 'CODER' | 'ADMIN';
/**
 * HIPAA audit log entry
 */
export interface HealthcareAuditLog {
    timestamp: string;
    userId: string;
    toolName: string;
    action: 'query' | 'view' | 'export';
    patientIdentifiers: string[];
    queryHash: string;
    resultCount: number;
    ipAddress: string;
    success: boolean;
    errorCode?: string;
    durationMs: number;
}
/**
 * Audit logger interface
 */
export interface AuditLogger {
    log: (entry: HealthcareAuditLog) => Promise<void>;
    query: (filter: Partial<HealthcareAuditLog>) => Promise<HealthcareAuditLog[]>;
}
/**
 * Role-based access control mapping
 */
export declare const HealthcareRolePermissions: Record<HealthcareRole, string[]>;
/**
 * HNSW Bridge interface for patient similarity
 */
export interface HNSWBridge {
    initialized: boolean;
    addVector: (id: string, vector: Float32Array, metadata?: Record<string, unknown>) => Promise<void>;
    search: (query: Float32Array, topK: number, filter?: Record<string, unknown>) => Promise<Array<{
        id: string;
        distance: number;
    }>>;
    delete: (id: string) => Promise<boolean>;
    count: () => Promise<number>;
    initialize: (config?: HNSWConfig) => Promise<void>;
}
/**
 * HNSW configuration
 */
export interface HNSWConfig {
    dimensions: number;
    maxElements?: number;
    efConstruction?: number;
    M?: number;
    efSearch?: number;
}
/**
 * GNN Bridge interface for clinical pathways
 */
export interface GNNBridge {
    initialized: boolean;
    loadGraph: (nodes: GNNNode[], edges: GNNEdge[]) => Promise<void>;
    predictPathway: (startNode: string, endNode: string, constraints?: Record<string, unknown>) => Promise<GNNPathResult>;
    analyzeInteractions: (nodeIds: string[]) => Promise<GNNInteractionResult>;
    initialize: (config?: GNNConfig) => Promise<void>;
}
/**
 * GNN node
 */
export interface GNNNode {
    id: string;
    type: string;
    features: number[];
    metadata?: Record<string, unknown>;
}
/**
 * GNN edge
 */
export interface GNNEdge {
    source: string;
    target: string;
    type: string;
    weight?: number;
    metadata?: Record<string, unknown>;
}
/**
 * GNN path prediction result
 */
export interface GNNPathResult {
    path: string[];
    confidence: number;
    alternativePaths: string[][];
    riskScore: number;
}
/**
 * GNN interaction analysis result
 */
export interface GNNInteractionResult {
    interactions: Array<{
        nodes: string[];
        type: string;
        strength: number;
        direction: string;
    }>;
    riskFactors: string[];
    recommendations: string[];
}
/**
 * GNN configuration
 */
export interface GNNConfig {
    hiddenDimensions?: number;
    numLayers?: number;
    dropout?: number;
    aggregationType?: 'mean' | 'sum' | 'max';
}
/**
 * Combined healthcare bridge interface
 */
export interface HealthcareBridge {
    hnsw?: HNSWBridge;
    gnn?: GNNBridge;
    initialized: boolean;
}
/**
 * Healthcare plugin configuration
 */
export interface HealthcareConfig {
    hipaa: {
        auditEnabled: boolean;
        encryptionRequired: boolean;
        minimumNecessary: boolean;
        retentionYears: number;
    };
    hnsw: HNSWConfig;
    gnn: GNNConfig;
    search: {
        defaultTopK: number;
        maxTopK: number;
        similarityThreshold: number;
    };
    cache: {
        enabled: boolean;
        ttl: number;
        maxSize: number;
    };
}
/**
 * Default configuration
 */
export declare const DEFAULT_HEALTHCARE_CONFIG: HealthcareConfig;
/**
 * Patient similarity input schema
 */
export declare const PatientSimilarityInputSchema: z.ZodObject<{
    patientFeatures: z.ZodObject<{
        diagnoses: z.ZodArray<z.ZodString, "many">;
        labResults: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        vitals: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        medications: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        demographics: z.ZodOptional<z.ZodObject<{
            ageRange: z.ZodOptional<z.ZodString>;
            gender: z.ZodOptional<z.ZodString>;
            ethnicity: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            ageRange?: string | undefined;
            gender?: string | undefined;
            ethnicity?: string | undefined;
        }, {
            ageRange?: string | undefined;
            gender?: string | undefined;
            ethnicity?: string | undefined;
        }>>;
        procedures: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        allergies: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        diagnoses: string[];
        labResults?: Record<string, number> | undefined;
        vitals?: Record<string, number> | undefined;
        medications?: string[] | undefined;
        demographics?: {
            ageRange?: string | undefined;
            gender?: string | undefined;
            ethnicity?: string | undefined;
        } | undefined;
        procedures?: string[] | undefined;
        allergies?: string[] | undefined;
    }, {
        diagnoses: string[];
        labResults?: Record<string, number> | undefined;
        vitals?: Record<string, number> | undefined;
        medications?: string[] | undefined;
        demographics?: {
            ageRange?: string | undefined;
            gender?: string | undefined;
            ethnicity?: string | undefined;
        } | undefined;
        procedures?: string[] | undefined;
        allergies?: string[] | undefined;
    }>;
    topK: z.ZodDefault<z.ZodNumber>;
    cohortFilter: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    patientFeatures: {
        diagnoses: string[];
        labResults?: Record<string, number> | undefined;
        vitals?: Record<string, number> | undefined;
        medications?: string[] | undefined;
        demographics?: {
            ageRange?: string | undefined;
            gender?: string | undefined;
            ethnicity?: string | undefined;
        } | undefined;
        procedures?: string[] | undefined;
        allergies?: string[] | undefined;
    };
    topK: number;
    cohortFilter?: string | undefined;
}, {
    patientFeatures: {
        diagnoses: string[];
        labResults?: Record<string, number> | undefined;
        vitals?: Record<string, number> | undefined;
        medications?: string[] | undefined;
        demographics?: {
            ageRange?: string | undefined;
            gender?: string | undefined;
            ethnicity?: string | undefined;
        } | undefined;
        procedures?: string[] | undefined;
        allergies?: string[] | undefined;
    };
    topK?: number | undefined;
    cohortFilter?: string | undefined;
}>;
/**
 * Drug interactions input schema
 */
export declare const DrugInteractionsInputSchema: z.ZodObject<{
    medications: z.ZodArray<z.ZodString, "many">;
    conditions: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    severity: z.ZodDefault<z.ZodEnum<["all", "major", "moderate", "minor"]>>;
}, "strip", z.ZodTypeAny, {
    medications: string[];
    severity: "major" | "moderate" | "minor" | "all";
    conditions?: string[] | undefined;
}, {
    medications: string[];
    conditions?: string[] | undefined;
    severity?: "major" | "moderate" | "minor" | "all" | undefined;
}>;
/**
 * Clinical pathways input schema
 */
export declare const ClinicalPathwaysInputSchema: z.ZodObject<{
    primaryDiagnosis: z.ZodString;
    patientHistory: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    constraints: z.ZodOptional<z.ZodObject<{
        excludeMedications: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        costSensitive: z.ZodOptional<z.ZodBoolean>;
        outpatientOnly: z.ZodOptional<z.ZodBoolean>;
        ageRestrictions: z.ZodOptional<z.ZodString>;
        comorbidityConsiderations: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        excludeMedications?: string[] | undefined;
        costSensitive?: boolean | undefined;
        outpatientOnly?: boolean | undefined;
        ageRestrictions?: string | undefined;
        comorbidityConsiderations?: string[] | undefined;
    }, {
        excludeMedications?: string[] | undefined;
        costSensitive?: boolean | undefined;
        outpatientOnly?: boolean | undefined;
        ageRestrictions?: string | undefined;
        comorbidityConsiderations?: string[] | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    primaryDiagnosis: string;
    patientHistory?: Record<string, unknown> | undefined;
    constraints?: {
        excludeMedications?: string[] | undefined;
        costSensitive?: boolean | undefined;
        outpatientOnly?: boolean | undefined;
        ageRestrictions?: string | undefined;
        comorbidityConsiderations?: string[] | undefined;
    } | undefined;
}, {
    primaryDiagnosis: string;
    patientHistory?: Record<string, unknown> | undefined;
    constraints?: {
        excludeMedications?: string[] | undefined;
        costSensitive?: boolean | undefined;
        outpatientOnly?: boolean | undefined;
        ageRestrictions?: string | undefined;
        comorbidityConsiderations?: string[] | undefined;
    } | undefined;
}>;
/**
 * Literature search input schema
 */
export declare const LiteratureSearchInputSchema: z.ZodObject<{
    query: z.ZodString;
    sources: z.ZodOptional<z.ZodArray<z.ZodEnum<["pubmed", "cochrane", "uptodate", "local"]>, "many">>;
    dateRange: z.ZodOptional<z.ZodObject<{
        from: z.ZodOptional<z.ZodString>;
        to: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        from?: string | undefined;
        to?: string | undefined;
    }, {
        from?: string | undefined;
        to?: string | undefined;
    }>>;
    evidenceLevel: z.ZodOptional<z.ZodEnum<["any", "systematic-review", "rct", "cohort", "case-control", "case-series", "expert-opinion"]>>;
    maxResults: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    query: string;
    maxResults: number;
    sources?: ("pubmed" | "cochrane" | "uptodate" | "local")[] | undefined;
    dateRange?: {
        from?: string | undefined;
        to?: string | undefined;
    } | undefined;
    evidenceLevel?: "systematic-review" | "rct" | "cohort" | "case-control" | "case-series" | "expert-opinion" | "any" | undefined;
}, {
    query: string;
    sources?: ("pubmed" | "cochrane" | "uptodate" | "local")[] | undefined;
    dateRange?: {
        from?: string | undefined;
        to?: string | undefined;
    } | undefined;
    evidenceLevel?: "systematic-review" | "rct" | "cohort" | "case-control" | "case-series" | "expert-opinion" | "any" | undefined;
    maxResults?: number | undefined;
}>;
/**
 * Ontology navigation input schema
 */
export declare const OntologyNavigationInputSchema: z.ZodObject<{
    code: z.ZodString;
    ontology: z.ZodEnum<["icd10", "snomed", "loinc", "rxnorm"]>;
    direction: z.ZodEnum<["ancestors", "descendants", "siblings", "related"]>;
    depth: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    code: string;
    ontology: "icd10" | "snomed" | "loinc" | "rxnorm";
    direction: "ancestors" | "descendants" | "siblings" | "related";
    depth: number;
}, {
    code: string;
    ontology: "icd10" | "snomed" | "loinc" | "rxnorm";
    direction: "ancestors" | "descendants" | "siblings" | "related";
    depth?: number | undefined;
}>;
/**
 * Create a success result
 */
export declare function successResult<T>(data: T, metadata?: MCPToolResult['metadata']): MCPToolResult;
/**
 * Create an error result
 */
export declare function errorResult(error: string | Error, metadata?: MCPToolResult['metadata']): MCPToolResult;
/**
 * Healthcare plugin error codes
 */
export declare const HealthcareErrorCodes: {
    readonly HIPAA_VIOLATION: "HC_HIPAA_VIOLATION";
    readonly UNAUTHORIZED_ACCESS: "HC_UNAUTHORIZED_ACCESS";
    readonly INVALID_ICD10_CODE: "HC_INVALID_ICD10_CODE";
    readonly INVALID_SNOMED_CODE: "HC_INVALID_SNOMED_CODE";
    readonly PATIENT_NOT_FOUND: "HC_PATIENT_NOT_FOUND";
    readonly DRUG_NOT_FOUND: "HC_DRUG_NOT_FOUND";
    readonly ONTOLOGY_NOT_AVAILABLE: "HC_ONTOLOGY_NOT_AVAILABLE";
    readonly WASM_NOT_INITIALIZED: "HC_WASM_NOT_INITIALIZED";
    readonly SEARCH_FAILED: "HC_SEARCH_FAILED";
    readonly AUDIT_FAILED: "HC_AUDIT_FAILED";
};
export type HealthcareErrorCode = (typeof HealthcareErrorCodes)[keyof typeof HealthcareErrorCodes];
//# sourceMappingURL=types.d.ts.map