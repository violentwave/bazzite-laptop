/**
 * Agentic-QE Plugin Entry Point
 * Plugin exports for claude-flow V3 integration
 *
 * @module v3/plugins/agentic-qe
 * @version 3.2.3
 */
// =============================================================================
// Main Plugin Export
// =============================================================================
export { AQEPlugin } from './plugin.js';
// Create default plugin instance
import { AQEPlugin } from './plugin.js';
export const agenticQEPlugin = new AQEPlugin();
export default agenticQEPlugin;
// =============================================================================
// Schema Exports
// =============================================================================
export { 
// Base Schemas
TestTypeSchema, TDDStyleSchema, TestFrameworkSchema, SecurityLevelSchema, ModelTierSchema, ContractTypeSchema, ChaosFailureTypeSchema, ComplianceStandardSchema, SecurityScanTypeSchema, SeveritySchema, QualityGateOperatorSchema, CoverageAlgorithmSchema, BoundedContextSchema, 
// Request Schemas
TestGenerationRequestSchema, TDDCycleRequestSchema, CoverageAnalysisRequestSchema, QualityGateRequestSchema, DefectPredictionRequestSchema, SecurityScanRequestSchema, ContractValidationRequestSchema, ChaosInjectionRequestSchema, VisualRegressionRequestSchema, AccessibilityCheckRequestSchema, 
// Configuration Schemas
PluginConfigSchema, SandboxConfigSchema, ModelRoutingConfigSchema, HNSWConfigSchema, MemoryNamespaceSchema, 
// MCP Tool Input Schemas
GenerateTestsInputSchema, AnalyzeCoverageInputSchema, SecurityScanInputSchema, ValidateContractInputSchema, ChaosInjectInputSchema, EvaluateQualityGateInputSchema, PredictDefectsInputSchema, TDDCycleInputSchema, 
// Validation Helpers
validateInput, parseOrThrow, parseWithDefaults, } from './schemas.js';
// =============================================================================
// Plugin Metadata
// =============================================================================
/**
 * Plugin metadata for registration
 */
export const PLUGIN_METADATA = {
    name: 'agentic-qe',
    version: '3.2.3',
    description: 'Quality Engineering plugin with 51 specialized agents across 12 DDD bounded contexts',
    author: 'rUv',
    license: 'MIT',
    homepage: 'https://github.com/ruvnet/agentic-qe',
    repository: 'https://github.com/ruvnet/agentic-qe',
    minClaudeFlowVersion: '3.0.0-alpha.50',
    capabilities: [
        'test-generation',
        'test-execution',
        'coverage-analysis',
        'quality-assessment',
        'defect-intelligence',
        'requirements-validation',
        'code-intelligence',
        'security-compliance',
        'contract-testing',
        'visual-accessibility',
        'chaos-resilience',
        'learning-optimization',
    ],
    dependencies: {
        required: [
            '@claude-flow/plugins',
            '@claude-flow/memory',
            '@claude-flow/security',
            '@claude-flow/embeddings',
        ],
        optional: [
            '@claude-flow/browser',
            '@ruvector/attention',
            '@ruvector/gnn',
            '@ruvector/sona',
        ],
    },
};
/**
 * Plugin performance targets
 */
export const PERFORMANCE_TARGETS = {
    testGenerationLatency: '<2s',
    coverageAnalysis: 'O(log n)',
    qualityGateEvaluation: '<500ms',
    securityScanPerKLOC: '<10s',
    mcpToolResponse: '<100ms',
    memoryPerContext: '<50MB',
};
/**
 * Bounded context agent counts
 */
export const CONTEXT_AGENT_COUNTS = {
    'test-generation': 12,
    'test-execution': 8,
    'coverage-analysis': 6,
    'quality-assessment': 5,
    'defect-intelligence': 4,
    'requirements-validation': 3,
    'code-intelligence': 5,
    'security-compliance': 4,
    'contract-testing': 3,
    'visual-accessibility': 3,
    'chaos-resilience': 4,
    'learning-optimization': 2,
    'tdd': 7, // TDD subagents
};
/**
 * Total agent count
 */
export const TOTAL_AGENT_COUNT = 51 + 7; // 51 context agents + 7 TDD subagents
//# sourceMappingURL=index.js.map