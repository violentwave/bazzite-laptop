/**
 * Healthcare Clinical Plugin - Type Definitions
 *
 * Core types for HIPAA-compliant clinical decision support including
 * patient similarity, drug interactions, clinical pathways, literature search,
 * and medical ontology navigation.
 */
import { z } from 'zod';
/**
 * Role-based access control mapping
 */
export const HealthcareRolePermissions = {
    PHYSICIAN: ['patient-similarity', 'drug-interactions', 'clinical-pathways', 'literature-search', 'ontology-navigate'],
    NURSE: ['drug-interactions', 'ontology-navigate'],
    PHARMACIST: ['drug-interactions', 'literature-search'],
    RESEARCHER: ['literature-search', 'ontology-navigate'],
    CODER: ['ontology-navigate'],
    ADMIN: ['patient-similarity', 'drug-interactions', 'clinical-pathways', 'literature-search', 'ontology-navigate'],
};
/**
 * Default configuration
 */
export const DEFAULT_HEALTHCARE_CONFIG = {
    hipaa: {
        auditEnabled: true,
        encryptionRequired: true,
        minimumNecessary: true,
        retentionYears: 6,
    },
    hnsw: {
        dimensions: 768,
        maxElements: 100000,
        efConstruction: 200,
        M: 16,
        efSearch: 100,
    },
    gnn: {
        hiddenDimensions: 256,
        numLayers: 3,
        dropout: 0.1,
        aggregationType: 'mean',
    },
    search: {
        defaultTopK: 5,
        maxTopK: 100,
        similarityThreshold: 0.7,
    },
    cache: {
        enabled: true,
        ttl: 300000,
        maxSize: 1000,
    },
};
// ============================================================================
// Zod Schemas for Input Validation
// ============================================================================
/**
 * ICD-10 code format validation
 */
const ICD10CodeSchema = z.string().regex(/^[A-Z]\d{2}(\.\d{1,2})?$/, 'Invalid ICD-10 code format');
/**
 * Patient similarity input schema
 */
export const PatientSimilarityInputSchema = z.object({
    patientFeatures: z.object({
        diagnoses: z.array(ICD10CodeSchema).max(100),
        labResults: z.record(z.string(), z.number()).optional(),
        vitals: z.record(z.string(), z.number()).optional(),
        medications: z.array(z.string().max(200)).max(50).optional(),
        demographics: z.object({
            ageRange: z.string().optional(),
            gender: z.string().optional(),
            ethnicity: z.string().optional(),
        }).optional(),
        procedures: z.array(z.string().max(200)).max(100).optional(),
        allergies: z.array(z.string().max(200)).max(50).optional(),
    }),
    topK: z.number().int().min(1).max(100).default(5),
    cohortFilter: z.string().max(500).optional(),
});
/**
 * Drug interactions input schema
 */
export const DrugInteractionsInputSchema = z.object({
    medications: z.array(z.string().max(200)).min(1).max(50),
    conditions: z.array(z.string().max(200)).max(100).optional(),
    severity: z.enum(['all', 'major', 'moderate', 'minor']).default('all'),
});
/**
 * Clinical pathways input schema
 */
export const ClinicalPathwaysInputSchema = z.object({
    primaryDiagnosis: z.string().max(100),
    patientHistory: z.record(z.string(), z.unknown()).optional(),
    constraints: z.object({
        excludeMedications: z.array(z.string()).optional(),
        costSensitive: z.boolean().optional(),
        outpatientOnly: z.boolean().optional(),
        ageRestrictions: z.string().optional(),
        comorbidityConsiderations: z.array(z.string()).optional(),
    }).optional(),
});
/**
 * Literature search input schema
 */
export const LiteratureSearchInputSchema = z.object({
    query: z.string().min(3).max(1000),
    sources: z.array(z.enum(['pubmed', 'cochrane', 'uptodate', 'local'])).optional(),
    dateRange: z.object({
        from: z.string().datetime().optional(),
        to: z.string().datetime().optional(),
    }).optional(),
    evidenceLevel: z.enum(['any', 'systematic-review', 'rct', 'cohort', 'case-control', 'case-series', 'expert-opinion']).optional(),
    maxResults: z.number().int().min(1).max(100).default(20),
});
/**
 * Ontology navigation input schema
 */
export const OntologyNavigationInputSchema = z.object({
    code: z.string().max(50),
    ontology: z.enum(['icd10', 'snomed', 'loinc', 'rxnorm']),
    direction: z.enum(['ancestors', 'descendants', 'siblings', 'related']),
    depth: z.number().int().min(1).max(10).default(2),
});
// ============================================================================
// Result Helpers
// ============================================================================
/**
 * Create a success result
 */
export function successResult(data, metadata) {
    return {
        success: true,
        data,
        metadata,
    };
}
/**
 * Create an error result
 */
export function errorResult(error, metadata) {
    return {
        success: false,
        error: error instanceof Error ? error.message : error,
        metadata,
    };
}
// ============================================================================
// Error Codes
// ============================================================================
/**
 * Healthcare plugin error codes
 */
export const HealthcareErrorCodes = {
    HIPAA_VIOLATION: 'HC_HIPAA_VIOLATION',
    UNAUTHORIZED_ACCESS: 'HC_UNAUTHORIZED_ACCESS',
    INVALID_ICD10_CODE: 'HC_INVALID_ICD10_CODE',
    INVALID_SNOMED_CODE: 'HC_INVALID_SNOMED_CODE',
    PATIENT_NOT_FOUND: 'HC_PATIENT_NOT_FOUND',
    DRUG_NOT_FOUND: 'HC_DRUG_NOT_FOUND',
    ONTOLOGY_NOT_AVAILABLE: 'HC_ONTOLOGY_NOT_AVAILABLE',
    WASM_NOT_INITIALIZED: 'HC_WASM_NOT_INITIALIZED',
    SEARCH_FAILED: 'HC_SEARCH_FAILED',
    AUDIT_FAILED: 'HC_AUDIT_FAILED',
};
//# sourceMappingURL=types.js.map