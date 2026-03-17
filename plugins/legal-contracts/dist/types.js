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
// ============================================================================
// Clause Types
// ============================================================================
/**
 * Supported clause types for extraction
 */
export const ClauseType = z.enum([
    'indemnification',
    'limitation_of_liability',
    'termination',
    'confidentiality',
    'ip_assignment',
    'governing_law',
    'arbitration',
    'force_majeure',
    'warranty',
    'payment_terms',
    'non_compete',
    'non_solicitation',
    'assignment',
    'insurance',
    'representations',
    'covenants',
    'data_protection',
    'audit_rights',
]);
// ============================================================================
// Risk Assessment Types
// ============================================================================
/**
 * Party role in the contract
 */
export const PartyRole = z.enum([
    'buyer',
    'seller',
    'licensor',
    'licensee',
    'employer',
    'employee',
    'landlord',
    'tenant',
    'lender',
    'borrower',
    'service_provider',
    'client',
]);
/**
 * Risk categories for assessment
 */
export const RiskCategory = z.enum([
    'financial',
    'operational',
    'legal',
    'reputational',
    'compliance',
    'strategic',
    'security',
    'performance',
]);
/**
 * Risk severity levels
 */
export const RiskSeverity = z.enum([
    'low',
    'medium',
    'high',
    'critical',
]);
// ============================================================================
// Contract Comparison Types
// ============================================================================
/**
 * Comparison mode for contract analysis
 */
export const ComparisonMode = z.enum([
    'structural', // Compare document structure only
    'semantic', // Compare meaning/intent
    'full', // Both structural and semantic
]);
// ============================================================================
// Obligation Tracking Types
// ============================================================================
/**
 * Obligation types
 */
export const ObligationType = z.enum([
    'payment',
    'delivery',
    'notification',
    'approval',
    'compliance',
    'reporting',
    'confidentiality',
    'performance',
    'insurance',
    'renewal',
    'termination',
]);
// ============================================================================
// Playbook Types
// ============================================================================
/**
 * Strictness level for playbook matching
 */
export const PlaybookStrictness = z.enum([
    'strict', // Exact match required
    'moderate', // Minor deviations acceptable
    'flexible', // Major deviations with justification
]);
/**
 * User role for access control
 */
export const UserRole = z.enum([
    'partner',
    'associate',
    'paralegal',
    'contract_manager',
    'client',
]);
/**
 * Tool access permissions by role
 */
export const RolePermissions = {
    partner: ['clause-extract', 'risk-assess', 'contract-compare', 'obligation-track', 'playbook-match'],
    associate: ['clause-extract', 'risk-assess', 'contract-compare', 'obligation-track'],
    paralegal: ['clause-extract', 'obligation-track'],
    contract_manager: ['obligation-track', 'playbook-match'],
    client: [], // No direct tool access
};
// ============================================================================
// MCP Tool Input Schemas
// ============================================================================
/**
 * Input schema for legal/clause-extract
 */
export const ClauseExtractInputSchema = z.object({
    document: z.string().max(10_000_000, 'Document size exceeds 10MB limit'),
    clauseTypes: z.array(ClauseType).optional(),
    jurisdiction: z.string().max(50).default('US'),
    includePositions: z.boolean().default(true),
    includeEmbeddings: z.boolean().default(false),
    matterContext: z.object({
        matterId: z.string(),
        clientId: z.string(),
    }).optional(),
});
/**
 * Input schema for legal/risk-assess
 */
export const RiskAssessInputSchema = z.object({
    document: z.string().max(10_000_000),
    partyRole: PartyRole,
    riskCategories: z.array(RiskCategory).optional(),
    industryContext: z.string().max(200).optional(),
    threshold: RiskSeverity.optional(),
    includeFinancialImpact: z.boolean().default(true),
    matterContext: z.object({
        matterId: z.string(),
        clientId: z.string(),
    }).optional(),
});
/**
 * Input schema for legal/contract-compare
 */
export const ContractCompareInputSchema = z.object({
    baseDocument: z.string().max(10_000_000),
    compareDocument: z.string().max(10_000_000),
    comparisonMode: ComparisonMode.default('full'),
    highlightChanges: z.boolean().default(true),
    generateRedline: z.boolean().default(false),
    focusClauseTypes: z.array(ClauseType).optional(),
    matterContext: z.object({
        matterId: z.string(),
        clientId: z.string(),
    }).optional(),
});
/**
 * Input schema for legal/obligation-track
 */
export const ObligationTrackInputSchema = z.object({
    document: z.string().max(10_000_000),
    party: z.string().max(200).optional(),
    timeframe: z.string().max(50).optional(),
    obligationTypes: z.array(ObligationType).optional(),
    includeDependencies: z.boolean().default(true),
    includeTimeline: z.boolean().default(true),
    matterContext: z.object({
        matterId: z.string(),
        clientId: z.string(),
    }).optional(),
});
/**
 * Input schema for legal/playbook-match
 */
export const PlaybookMatchInputSchema = z.object({
    document: z.string().max(10_000_000),
    playbook: z.string().max(1_000_000, 'Playbook size exceeds 1MB limit'),
    strictness: PlaybookStrictness.default('moderate'),
    suggestAlternatives: z.boolean().default(true),
    prioritizeClauses: z.array(ClauseType).optional(),
    matterContext: z.object({
        matterId: z.string(),
        clientId: z.string(),
    }).optional(),
});
/**
 * Default configuration
 */
export const DEFAULT_CONFIG = {
    extraction: {
        minConfidence: 0.7,
        includeEmbeddings: false,
        embeddingDimension: 384,
    },
    risk: {
        defaultThreshold: 'medium',
        includeFinancialImpact: true,
    },
    comparison: {
        similarityThreshold: 0.8,
        generateRedline: false,
    },
    security: {
        matterIsolation: true,
        auditLevel: 'standard',
        allowedDocumentRoot: '/documents',
    },
};
// ============================================================================
// Error Types
// ============================================================================
/**
 * Legal contracts plugin error codes
 */
export const LegalErrorCodes = {
    DOCUMENT_TOO_LARGE: 'LEGAL_DOCUMENT_TOO_LARGE',
    INVALID_DOCUMENT_FORMAT: 'LEGAL_INVALID_DOCUMENT_FORMAT',
    CLAUSE_EXTRACTION_FAILED: 'LEGAL_CLAUSE_EXTRACTION_FAILED',
    RISK_ASSESSMENT_FAILED: 'LEGAL_RISK_ASSESSMENT_FAILED',
    COMPARISON_FAILED: 'LEGAL_COMPARISON_FAILED',
    OBLIGATION_PARSING_FAILED: 'LEGAL_OBLIGATION_PARSING_FAILED',
    PLAYBOOK_INVALID: 'LEGAL_PLAYBOOK_INVALID',
    MATTER_ACCESS_DENIED: 'LEGAL_MATTER_ACCESS_DENIED',
    ETHICAL_WALL_VIOLATION: 'LEGAL_ETHICAL_WALL_VIOLATION',
    WASM_NOT_INITIALIZED: 'LEGAL_WASM_NOT_INITIALIZED',
    PRIVILEGE_VIOLATION: 'LEGAL_PRIVILEGE_VIOLATION',
};
/**
 * Legal contracts plugin error
 */
export class LegalContractsError extends Error {
    code;
    details;
    constructor(code, message, details) {
        super(message);
        this.name = 'LegalContractsError';
        this.code = code;
        this.details = details;
    }
}
//# sourceMappingURL=types.js.map