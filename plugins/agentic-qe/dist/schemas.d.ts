/**
 * Agentic-QE Plugin Zod Schemas
 * Input validation schemas for all QE operations
 *
 * @module v3/plugins/agentic-qe/schemas
 * @version 3.2.3
 */
import { z } from 'zod';
/**
 * Test type enum schema
 */
export declare const TestTypeSchema: z.ZodEnum<["unit", "integration", "e2e", "property", "mutation", "fuzz", "api", "performance", "security", "accessibility", "contract", "bdd"]>;
/**
 * TDD style enum schema
 */
export declare const TDDStyleSchema: z.ZodEnum<["london", "chicago"]>;
/**
 * Test framework enum schema
 */
export declare const TestFrameworkSchema: z.ZodEnum<["vitest", "jest", "mocha", "pytest", "junit", "xunit", "nunit", "playwright", "cypress"]>;
/**
 * Security level enum schema
 */
export declare const SecurityLevelSchema: z.ZodEnum<["low", "medium", "high", "critical"]>;
/**
 * Model tier enum schema
 */
export declare const ModelTierSchema: z.ZodEnum<["agent-booster", "haiku", "sonnet", "opus"]>;
/**
 * Contract type enum schema
 */
export declare const ContractTypeSchema: z.ZodEnum<["openapi", "graphql", "grpc", "asyncapi"]>;
/**
 * Chaos failure type enum schema
 */
export declare const ChaosFailureTypeSchema: z.ZodEnum<["network-latency", "network-partition", "cpu-stress", "memory-pressure", "disk-failure", "process-kill"]>;
/**
 * Compliance standard enum schema
 */
export declare const ComplianceStandardSchema: z.ZodEnum<["owasp-top-10", "sans-25", "pci-dss", "hipaa", "gdpr", "soc2"]>;
/**
 * Security scan type enum schema
 */
export declare const SecurityScanTypeSchema: z.ZodEnum<["sast", "dast", "both"]>;
/**
 * Severity enum schema
 */
export declare const SeveritySchema: z.ZodEnum<["critical", "high", "medium", "low", "info"]>;
/**
 * Quality gate operator enum schema
 */
export declare const QualityGateOperatorSchema: z.ZodEnum<[">", "<", ">=", "<=", "=="]>;
/**
 * Coverage algorithm enum schema
 */
export declare const CoverageAlgorithmSchema: z.ZodEnum<["johnson-lindenstrauss", "full-scan"]>;
/**
 * Bounded context enum schema
 */
export declare const BoundedContextSchema: z.ZodEnum<["test-generation", "test-execution", "coverage-analysis", "quality-assessment", "defect-intelligence", "requirements-validation", "code-intelligence", "security-compliance", "contract-testing", "visual-accessibility", "chaos-resilience", "learning-optimization"]>;
/**
 * Coverage configuration schema
 */
export declare const CoverageConfigSchema: z.ZodObject<{
    target: z.ZodDefault<z.ZodNumber>;
    focusGaps: z.ZodDefault<z.ZodBoolean>;
    includeBranches: z.ZodOptional<z.ZodBoolean>;
    includeFunctions: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    target: number;
    focusGaps: boolean;
    includeBranches?: boolean | undefined;
    includeFunctions?: boolean | undefined;
}, {
    target?: number | undefined;
    focusGaps?: boolean | undefined;
    includeBranches?: boolean | undefined;
    includeFunctions?: boolean | undefined;
}>;
/**
 * Test generation request schema
 */
export declare const TestGenerationRequestSchema: z.ZodObject<{
    targetPath: z.ZodString;
    testType: z.ZodDefault<z.ZodEnum<["unit", "integration", "e2e", "property", "mutation", "fuzz", "api", "performance", "security", "accessibility", "contract", "bdd"]>>;
    framework: z.ZodOptional<z.ZodEnum<["vitest", "jest", "mocha", "pytest", "junit", "xunit", "nunit", "playwright", "cypress"]>>;
    coverage: z.ZodOptional<z.ZodObject<{
        target: z.ZodDefault<z.ZodNumber>;
        focusGaps: z.ZodDefault<z.ZodBoolean>;
        includeBranches: z.ZodOptional<z.ZodBoolean>;
        includeFunctions: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        target: number;
        focusGaps: boolean;
        includeBranches?: boolean | undefined;
        includeFunctions?: boolean | undefined;
    }, {
        target?: number | undefined;
        focusGaps?: boolean | undefined;
        includeBranches?: boolean | undefined;
        includeFunctions?: boolean | undefined;
    }>>;
    style: z.ZodDefault<z.ZodEnum<["london", "chicago"]>>;
    context: z.ZodOptional<z.ZodString>;
    language: z.ZodOptional<z.ZodString>;
    maxTests: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    testType: "unit" | "integration" | "e2e" | "property" | "mutation" | "fuzz" | "api" | "performance" | "security" | "accessibility" | "contract" | "bdd";
    style: "london" | "chicago";
    framework?: "vitest" | "jest" | "mocha" | "pytest" | "junit" | "xunit" | "nunit" | "playwright" | "cypress" | undefined;
    coverage?: {
        target: number;
        focusGaps: boolean;
        includeBranches?: boolean | undefined;
        includeFunctions?: boolean | undefined;
    } | undefined;
    context?: string | undefined;
    language?: string | undefined;
    maxTests?: number | undefined;
}, {
    targetPath: string;
    testType?: "unit" | "integration" | "e2e" | "property" | "mutation" | "fuzz" | "api" | "performance" | "security" | "accessibility" | "contract" | "bdd" | undefined;
    framework?: "vitest" | "jest" | "mocha" | "pytest" | "junit" | "xunit" | "nunit" | "playwright" | "cypress" | undefined;
    coverage?: {
        target?: number | undefined;
        focusGaps?: boolean | undefined;
        includeBranches?: boolean | undefined;
        includeFunctions?: boolean | undefined;
    } | undefined;
    style?: "london" | "chicago" | undefined;
    context?: string | undefined;
    language?: string | undefined;
    maxTests?: number | undefined;
}>;
/**
 * TDD cycle request schema
 */
export declare const TDDCycleRequestSchema: z.ZodObject<{
    requirement: z.ZodString;
    targetPath: z.ZodString;
    style: z.ZodDefault<z.ZodEnum<["london", "chicago"]>>;
    maxCycles: z.ZodDefault<z.ZodNumber>;
    framework: z.ZodOptional<z.ZodEnum<["vitest", "jest", "mocha", "pytest", "junit", "xunit", "nunit", "playwright", "cypress"]>>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    style: "london" | "chicago";
    requirement: string;
    maxCycles: number;
    framework?: "vitest" | "jest" | "mocha" | "pytest" | "junit" | "xunit" | "nunit" | "playwright" | "cypress" | undefined;
}, {
    targetPath: string;
    requirement: string;
    framework?: "vitest" | "jest" | "mocha" | "pytest" | "junit" | "xunit" | "nunit" | "playwright" | "cypress" | undefined;
    style?: "london" | "chicago" | undefined;
    maxCycles?: number | undefined;
}>;
/**
 * Coverage analysis request schema
 */
export declare const CoverageAnalysisRequestSchema: z.ZodObject<{
    coverageReport: z.ZodOptional<z.ZodString>;
    targetPath: z.ZodString;
    algorithm: z.ZodDefault<z.ZodEnum<["johnson-lindenstrauss", "full-scan"]>>;
    prioritize: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    algorithm: "johnson-lindenstrauss" | "full-scan";
    prioritize: boolean;
    coverageReport?: string | undefined;
}, {
    targetPath: string;
    coverageReport?: string | undefined;
    algorithm?: "johnson-lindenstrauss" | "full-scan" | undefined;
    prioritize?: boolean | undefined;
}>;
/**
 * Quality gate schema
 */
export declare const QualityGateSchema: z.ZodObject<{
    id: z.ZodOptional<z.ZodString>;
    name: z.ZodOptional<z.ZodString>;
    metric: z.ZodString;
    operator: z.ZodEnum<[">", "<", ">=", "<=", "=="]>;
    threshold: z.ZodNumber;
    blocking: z.ZodDefault<z.ZodBoolean>;
    description: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    metric: string;
    operator: ">" | "<" | ">=" | "<=" | "==";
    threshold: number;
    blocking: boolean;
    name?: string | undefined;
    id?: string | undefined;
    description?: string | undefined;
}, {
    metric: string;
    operator: ">" | "<" | ">=" | "<=" | "==";
    threshold: number;
    name?: string | undefined;
    id?: string | undefined;
    blocking?: boolean | undefined;
    description?: string | undefined;
}>;
/**
 * Quality gate request schema
 */
export declare const QualityGateRequestSchema: z.ZodObject<{
    gates: z.ZodOptional<z.ZodArray<z.ZodObject<{
        id: z.ZodOptional<z.ZodString>;
        name: z.ZodOptional<z.ZodString>;
        metric: z.ZodString;
        operator: z.ZodEnum<[">", "<", ">=", "<=", "=="]>;
        threshold: z.ZodNumber;
        blocking: z.ZodDefault<z.ZodBoolean>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
        blocking: boolean;
        name?: string | undefined;
        id?: string | undefined;
        description?: string | undefined;
    }, {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
        name?: string | undefined;
        id?: string | undefined;
        blocking?: boolean | undefined;
        description?: string | undefined;
    }>, "many">>;
    defaults: z.ZodDefault<z.ZodEnum<["strict", "standard", "minimal"]>>;
    projectPath: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    defaults: "strict" | "standard" | "minimal";
    gates?: {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
        blocking: boolean;
        name?: string | undefined;
        id?: string | undefined;
        description?: string | undefined;
    }[] | undefined;
    projectPath?: string | undefined;
}, {
    gates?: {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
        name?: string | undefined;
        id?: string | undefined;
        blocking?: boolean | undefined;
        description?: string | undefined;
    }[] | undefined;
    defaults?: "strict" | "standard" | "minimal" | undefined;
    projectPath?: string | undefined;
}>;
/**
 * Defect prediction request schema
 */
export declare const DefectPredictionRequestSchema: z.ZodObject<{
    targetPath: z.ZodString;
    depth: z.ZodDefault<z.ZodEnum<["shallow", "medium", "deep"]>>;
    includeRootCause: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    depth: "medium" | "shallow" | "deep";
    includeRootCause: boolean;
}, {
    targetPath: string;
    depth?: "medium" | "shallow" | "deep" | undefined;
    includeRootCause?: boolean | undefined;
}>;
/**
 * Security scan request schema
 */
export declare const SecurityScanRequestSchema: z.ZodObject<{
    targetPath: z.ZodString;
    scanType: z.ZodDefault<z.ZodEnum<["sast", "dast", "both"]>>;
    compliance: z.ZodDefault<z.ZodArray<z.ZodEnum<["owasp-top-10", "sans-25", "pci-dss", "hipaa", "gdpr", "soc2"]>, "many">>;
    severityFilter: z.ZodDefault<z.ZodUnion<[z.ZodLiteral<"all">, z.ZodEnum<["critical", "high", "medium", "low", "info"]>]>>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    scanType: "sast" | "dast" | "both";
    compliance: ("owasp-top-10" | "sans-25" | "pci-dss" | "hipaa" | "gdpr" | "soc2")[];
    severityFilter: "critical" | "high" | "medium" | "low" | "info" | "all";
}, {
    targetPath: string;
    scanType?: "sast" | "dast" | "both" | undefined;
    compliance?: ("owasp-top-10" | "sans-25" | "pci-dss" | "hipaa" | "gdpr" | "soc2")[] | undefined;
    severityFilter?: "critical" | "high" | "medium" | "low" | "info" | "all" | undefined;
}>;
/**
 * Contract validation request schema
 */
export declare const ContractValidationRequestSchema: z.ZodObject<{
    contractPath: z.ZodString;
    contractType: z.ZodEnum<["openapi", "graphql", "grpc", "asyncapi"]>;
    targetUrl: z.ZodOptional<z.ZodString>;
    strict: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    strict: boolean;
    contractPath: string;
    contractType: "openapi" | "graphql" | "grpc" | "asyncapi";
    targetUrl?: string | undefined;
}, {
    contractPath: string;
    contractType: "openapi" | "graphql" | "grpc" | "asyncapi";
    strict?: boolean | undefined;
    targetUrl?: string | undefined;
}>;
/**
 * Contract comparison request schema
 */
export declare const ContractComparisonRequestSchema: z.ZodObject<{
    oldContractPath: z.ZodString;
    newContractPath: z.ZodString;
    contractType: z.ZodEnum<["openapi", "graphql", "grpc", "asyncapi"]>;
    strict: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    strict: boolean;
    contractType: "openapi" | "graphql" | "grpc" | "asyncapi";
    oldContractPath: string;
    newContractPath: string;
}, {
    contractType: "openapi" | "graphql" | "grpc" | "asyncapi";
    oldContractPath: string;
    newContractPath: string;
    strict?: boolean | undefined;
}>;
/**
 * Chaos injection request schema
 */
export declare const ChaosInjectionRequestSchema: z.ZodObject<{
    target: z.ZodString;
    failureType: z.ZodEnum<["network-latency", "network-partition", "cpu-stress", "memory-pressure", "disk-failure", "process-kill"]>;
    duration: z.ZodDefault<z.ZodNumber>;
    intensity: z.ZodDefault<z.ZodNumber>;
    dryRun: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    target: string;
    failureType: "network-latency" | "network-partition" | "cpu-stress" | "memory-pressure" | "disk-failure" | "process-kill";
    duration: number;
    intensity: number;
    dryRun: boolean;
}, {
    target: string;
    failureType: "network-latency" | "network-partition" | "cpu-stress" | "memory-pressure" | "disk-failure" | "process-kill";
    duration?: number | undefined;
    intensity?: number | undefined;
    dryRun?: boolean | undefined;
}>;
/**
 * Resilience assessment request schema
 */
export declare const ResilienceAssessmentRequestSchema: z.ZodObject<{
    experimentId: z.ZodString;
    includeRecommendations: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    experimentId: string;
    includeRecommendations: boolean;
}, {
    experimentId: string;
    includeRecommendations?: boolean | undefined;
}>;
/**
 * Visual regression request schema
 */
export declare const VisualRegressionRequestSchema: z.ZodObject<{
    targetUrl: z.ZodString;
    componentSelector: z.ZodOptional<z.ZodString>;
    viewport: z.ZodOptional<z.ZodObject<{
        width: z.ZodNumber;
        height: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        width: number;
        height: number;
    }, {
        width: number;
        height: number;
    }>>;
    threshold: z.ZodDefault<z.ZodNumber>;
    updateBaseline: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    threshold: number;
    targetUrl: string;
    updateBaseline: boolean;
    componentSelector?: string | undefined;
    viewport?: {
        width: number;
        height: number;
    } | undefined;
}, {
    targetUrl: string;
    threshold?: number | undefined;
    componentSelector?: string | undefined;
    viewport?: {
        width: number;
        height: number;
    } | undefined;
    updateBaseline?: boolean | undefined;
}>;
/**
 * Accessibility check request schema
 */
export declare const AccessibilityCheckRequestSchema: z.ZodObject<{
    targetUrl: z.ZodString;
    wcagLevel: z.ZodDefault<z.ZodEnum<["A", "AA", "AAA"]>>;
    includeWarnings: z.ZodDefault<z.ZodBoolean>;
    selector: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    targetUrl: string;
    wcagLevel: "A" | "AA" | "AAA";
    includeWarnings: boolean;
    selector?: string | undefined;
}, {
    targetUrl: string;
    wcagLevel?: "A" | "AA" | "AAA" | undefined;
    includeWarnings?: boolean | undefined;
    selector?: string | undefined;
}>;
/**
 * HNSW configuration schema
 */
export declare const HNSWConfigSchema: z.ZodObject<{
    m: z.ZodDefault<z.ZodNumber>;
    efConstruction: z.ZodDefault<z.ZodNumber>;
    efSearch: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    m: number;
    efConstruction: number;
    efSearch: number;
}, {
    m?: number | undefined;
    efConstruction?: number | undefined;
    efSearch?: number | undefined;
}>;
/**
 * Sandbox configuration schema
 */
export declare const SandboxConfigSchema: z.ZodObject<{
    maxExecutionTime: z.ZodDefault<z.ZodNumber>;
    memoryLimit: z.ZodDefault<z.ZodNumber>;
    networkPolicy: z.ZodDefault<z.ZodEnum<["unrestricted", "restricted", "blocked"]>>;
    fileSystemPolicy: z.ZodDefault<z.ZodEnum<["full", "workspace-only", "readonly", "none"]>>;
    allowedCommands: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    blockedPaths: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    maxExecutionTime: number;
    memoryLimit: number;
    networkPolicy: "unrestricted" | "restricted" | "blocked";
    fileSystemPolicy: "full" | "workspace-only" | "readonly" | "none";
    allowedCommands: string[];
    blockedPaths: string[];
}, {
    maxExecutionTime?: number | undefined;
    memoryLimit?: number | undefined;
    networkPolicy?: "unrestricted" | "restricted" | "blocked" | undefined;
    fileSystemPolicy?: "full" | "workspace-only" | "readonly" | "none" | undefined;
    allowedCommands?: string[] | undefined;
    blockedPaths?: string[] | undefined;
}>;
/**
 * Model routing configuration schema
 */
export declare const ModelRoutingConfigSchema: z.ZodObject<{
    enabled: z.ZodDefault<z.ZodBoolean>;
    preferCost: z.ZodDefault<z.ZodBoolean>;
    thresholds: z.ZodDefault<z.ZodObject<{
        tier1MaxComplexity: z.ZodDefault<z.ZodNumber>;
        tier2MaxComplexity: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        tier1MaxComplexity: number;
        tier2MaxComplexity: number;
    }, {
        tier1MaxComplexity?: number | undefined;
        tier2MaxComplexity?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    enabled: boolean;
    preferCost: boolean;
    thresholds: {
        tier1MaxComplexity: number;
        tier2MaxComplexity: number;
    };
}, {
    enabled?: boolean | undefined;
    preferCost?: boolean | undefined;
    thresholds?: {
        tier1MaxComplexity?: number | undefined;
        tier2MaxComplexity?: number | undefined;
    } | undefined;
}>;
/**
 * Performance targets schema
 */
export declare const PerformanceTargetsSchema: z.ZodObject<{
    testGenerationLatency: z.ZodDefault<z.ZodString>;
    coverageAnalysis: z.ZodDefault<z.ZodString>;
    qualityGateEvaluation: z.ZodDefault<z.ZodString>;
    securityScanPerKLOC: z.ZodDefault<z.ZodString>;
    mcpToolResponse: z.ZodDefault<z.ZodString>;
    memoryPerContext: z.ZodDefault<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    testGenerationLatency: string;
    coverageAnalysis: string;
    qualityGateEvaluation: string;
    securityScanPerKLOC: string;
    mcpToolResponse: string;
    memoryPerContext: string;
}, {
    testGenerationLatency?: string | undefined;
    coverageAnalysis?: string | undefined;
    qualityGateEvaluation?: string | undefined;
    securityScanPerKLOC?: string | undefined;
    mcpToolResponse?: string | undefined;
    memoryPerContext?: string | undefined;
}>;
/**
 * Plugin configuration schema
 */
export declare const PluginConfigSchema: z.ZodObject<{
    version: z.ZodDefault<z.ZodString>;
    namespacePrefix: z.ZodDefault<z.ZodString>;
    enabledContexts: z.ZodDefault<z.ZodArray<z.ZodEnum<["test-generation", "test-execution", "coverage-analysis", "quality-assessment", "defect-intelligence", "requirements-validation", "code-intelligence", "security-compliance", "contract-testing", "visual-accessibility", "chaos-resilience", "learning-optimization"]>, "many">>;
    sandbox: z.ZodDefault<z.ZodObject<{
        maxExecutionTime: z.ZodDefault<z.ZodNumber>;
        memoryLimit: z.ZodDefault<z.ZodNumber>;
        networkPolicy: z.ZodDefault<z.ZodEnum<["unrestricted", "restricted", "blocked"]>>;
        fileSystemPolicy: z.ZodDefault<z.ZodEnum<["full", "workspace-only", "readonly", "none"]>>;
        allowedCommands: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
        blockedPaths: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        maxExecutionTime: number;
        memoryLimit: number;
        networkPolicy: "unrestricted" | "restricted" | "blocked";
        fileSystemPolicy: "full" | "workspace-only" | "readonly" | "none";
        allowedCommands: string[];
        blockedPaths: string[];
    }, {
        maxExecutionTime?: number | undefined;
        memoryLimit?: number | undefined;
        networkPolicy?: "unrestricted" | "restricted" | "blocked" | undefined;
        fileSystemPolicy?: "full" | "workspace-only" | "readonly" | "none" | undefined;
        allowedCommands?: string[] | undefined;
        blockedPaths?: string[] | undefined;
    }>>;
    modelRouting: z.ZodDefault<z.ZodObject<{
        enabled: z.ZodDefault<z.ZodBoolean>;
        preferCost: z.ZodDefault<z.ZodBoolean>;
        thresholds: z.ZodDefault<z.ZodObject<{
            tier1MaxComplexity: z.ZodDefault<z.ZodNumber>;
            tier2MaxComplexity: z.ZodDefault<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            tier1MaxComplexity: number;
            tier2MaxComplexity: number;
        }, {
            tier1MaxComplexity?: number | undefined;
            tier2MaxComplexity?: number | undefined;
        }>>;
    }, "strip", z.ZodTypeAny, {
        enabled: boolean;
        preferCost: boolean;
        thresholds: {
            tier1MaxComplexity: number;
            tier2MaxComplexity: number;
        };
    }, {
        enabled?: boolean | undefined;
        preferCost?: boolean | undefined;
        thresholds?: {
            tier1MaxComplexity?: number | undefined;
            tier2MaxComplexity?: number | undefined;
        } | undefined;
    }>>;
    performanceTargets: z.ZodDefault<z.ZodObject<{
        testGenerationLatency: z.ZodDefault<z.ZodString>;
        coverageAnalysis: z.ZodDefault<z.ZodString>;
        qualityGateEvaluation: z.ZodDefault<z.ZodString>;
        securityScanPerKLOC: z.ZodDefault<z.ZodString>;
        mcpToolResponse: z.ZodDefault<z.ZodString>;
        memoryPerContext: z.ZodDefault<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        testGenerationLatency: string;
        coverageAnalysis: string;
        qualityGateEvaluation: string;
        securityScanPerKLOC: string;
        mcpToolResponse: string;
        memoryPerContext: string;
    }, {
        testGenerationLatency?: string | undefined;
        coverageAnalysis?: string | undefined;
        qualityGateEvaluation?: string | undefined;
        securityScanPerKLOC?: string | undefined;
        mcpToolResponse?: string | undefined;
        memoryPerContext?: string | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    version: string;
    namespacePrefix: string;
    enabledContexts: ("test-generation" | "test-execution" | "coverage-analysis" | "quality-assessment" | "defect-intelligence" | "requirements-validation" | "code-intelligence" | "security-compliance" | "contract-testing" | "visual-accessibility" | "chaos-resilience" | "learning-optimization")[];
    sandbox: {
        maxExecutionTime: number;
        memoryLimit: number;
        networkPolicy: "unrestricted" | "restricted" | "blocked";
        fileSystemPolicy: "full" | "workspace-only" | "readonly" | "none";
        allowedCommands: string[];
        blockedPaths: string[];
    };
    modelRouting: {
        enabled: boolean;
        preferCost: boolean;
        thresholds: {
            tier1MaxComplexity: number;
            tier2MaxComplexity: number;
        };
    };
    performanceTargets: {
        testGenerationLatency: string;
        coverageAnalysis: string;
        qualityGateEvaluation: string;
        securityScanPerKLOC: string;
        mcpToolResponse: string;
        memoryPerContext: string;
    };
}, {
    version?: string | undefined;
    namespacePrefix?: string | undefined;
    enabledContexts?: ("test-generation" | "test-execution" | "coverage-analysis" | "quality-assessment" | "defect-intelligence" | "requirements-validation" | "code-intelligence" | "security-compliance" | "contract-testing" | "visual-accessibility" | "chaos-resilience" | "learning-optimization")[] | undefined;
    sandbox?: {
        maxExecutionTime?: number | undefined;
        memoryLimit?: number | undefined;
        networkPolicy?: "unrestricted" | "restricted" | "blocked" | undefined;
        fileSystemPolicy?: "full" | "workspace-only" | "readonly" | "none" | undefined;
        allowedCommands?: string[] | undefined;
        blockedPaths?: string[] | undefined;
    } | undefined;
    modelRouting?: {
        enabled?: boolean | undefined;
        preferCost?: boolean | undefined;
        thresholds?: {
            tier1MaxComplexity?: number | undefined;
            tier2MaxComplexity?: number | undefined;
        } | undefined;
    } | undefined;
    performanceTargets?: {
        testGenerationLatency?: string | undefined;
        coverageAnalysis?: string | undefined;
        qualityGateEvaluation?: string | undefined;
        securityScanPerKLOC?: string | undefined;
        mcpToolResponse?: string | undefined;
        memoryPerContext?: string | undefined;
    } | undefined;
}>;
/**
 * Schema field schema
 */
export declare const SchemaFieldSchema: z.ZodObject<{
    type: z.ZodEnum<["string", "number", "boolean", "object"]>;
    index: z.ZodOptional<z.ZodBoolean>;
    required: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    type: "string" | "number" | "boolean" | "object";
    index?: boolean | undefined;
    required?: boolean | undefined;
}, {
    type: "string" | "number" | "boolean" | "object";
    index?: boolean | undefined;
    required?: boolean | undefined;
}>;
/**
 * Memory namespace schema
 */
export declare const MemoryNamespaceSchema: z.ZodObject<{
    name: z.ZodString;
    description: z.ZodString;
    vectorDimension: z.ZodNumber;
    hnswConfig: z.ZodObject<{
        m: z.ZodDefault<z.ZodNumber>;
        efConstruction: z.ZodDefault<z.ZodNumber>;
        efSearch: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        m: number;
        efConstruction: number;
        efSearch: number;
    }, {
        m?: number | undefined;
        efConstruction?: number | undefined;
        efSearch?: number | undefined;
    }>;
    schema: z.ZodRecord<z.ZodString, z.ZodObject<{
        type: z.ZodEnum<["string", "number", "boolean", "object"]>;
        index: z.ZodOptional<z.ZodBoolean>;
        required: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        type: "string" | "number" | "boolean" | "object";
        index?: boolean | undefined;
        required?: boolean | undefined;
    }, {
        type: "string" | "number" | "boolean" | "object";
        index?: boolean | undefined;
        required?: boolean | undefined;
    }>>;
    ttl: z.ZodNullable<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    name: string;
    description: string;
    vectorDimension: number;
    hnswConfig: {
        m: number;
        efConstruction: number;
        efSearch: number;
    };
    schema: Record<string, {
        type: "string" | "number" | "boolean" | "object";
        index?: boolean | undefined;
        required?: boolean | undefined;
    }>;
    ttl: number | null;
}, {
    name: string;
    description: string;
    vectorDimension: number;
    hnswConfig: {
        m?: number | undefined;
        efConstruction?: number | undefined;
        efSearch?: number | undefined;
    };
    schema: Record<string, {
        type: "string" | "number" | "boolean" | "object";
        index?: boolean | undefined;
        required?: boolean | undefined;
    }>;
    ttl: number | null;
}>;
/**
 * Worker type schema
 */
export declare const WorkerTypeSchema: z.ZodEnum<["test-executor", "coverage-analyzer", "security-scanner"]>;
/**
 * Worker definition schema
 */
export declare const WorkerDefinitionSchema: z.ZodObject<{
    type: z.ZodEnum<["test-executor", "coverage-analyzer", "security-scanner"]>;
    capabilities: z.ZodArray<z.ZodString, "many">;
    maxConcurrent: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    type: "test-executor" | "coverage-analyzer" | "security-scanner";
    capabilities: string[];
    maxConcurrent: number;
}, {
    type: "test-executor" | "coverage-analyzer" | "security-scanner";
    capabilities: string[];
    maxConcurrent?: number | undefined;
}>;
/**
 * Worker dispatch request schema
 */
export declare const WorkerDispatchRequestSchema: z.ZodObject<{
    workerType: z.ZodEnum<["test-executor", "coverage-analyzer", "security-scanner"]>;
    payload: z.ZodUnknown;
    priority: z.ZodDefault<z.ZodEnum<["low", "normal", "high", "critical"]>>;
}, "strip", z.ZodTypeAny, {
    workerType: "test-executor" | "coverage-analyzer" | "security-scanner";
    priority: "critical" | "high" | "low" | "normal";
    payload?: unknown;
}, {
    workerType: "test-executor" | "coverage-analyzer" | "security-scanner";
    payload?: unknown;
    priority?: "critical" | "high" | "low" | "normal" | undefined;
}>;
/**
 * Hook event schema
 */
export declare const HookEventSchema: z.ZodEnum<["pre-test-execution", "pre-security-scan", "post-test-execution", "post-coverage-analysis", "post-security-scan"]>;
/**
 * Hook priority schema
 */
export declare const HookPrioritySchema: z.ZodEnum<["low", "normal", "high", "critical"]>;
/**
 * Hook definition schema
 */
export declare const HookDefinitionSchema: z.ZodObject<{
    event: z.ZodEnum<["pre-test-execution", "pre-security-scan", "post-test-execution", "post-coverage-analysis", "post-security-scan"]>;
    description: z.ZodString;
    priority: z.ZodDefault<z.ZodEnum<["low", "normal", "high", "critical"]>>;
    handler: z.ZodString;
}, "strip", z.ZodTypeAny, {
    event: "pre-test-execution" | "pre-security-scan" | "post-test-execution" | "post-coverage-analysis" | "post-security-scan";
    description: string;
    priority: "critical" | "high" | "low" | "normal";
    handler: string;
}, {
    event: "pre-test-execution" | "pre-security-scan" | "post-test-execution" | "post-coverage-analysis" | "post-security-scan";
    description: string;
    handler: string;
    priority?: "critical" | "high" | "low" | "normal" | undefined;
}>;
/**
 * Agent definition schema
 */
export declare const AgentDefinitionSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    context: z.ZodEnum<["test-generation", "test-execution", "coverage-analysis", "quality-assessment", "defect-intelligence", "requirements-validation", "code-intelligence", "security-compliance", "contract-testing", "visual-accessibility", "chaos-resilience", "learning-optimization"]>;
    capabilities: z.ZodArray<z.ZodString, "many">;
    modelTier: z.ZodDefault<z.ZodEnum<["agent-booster", "haiku", "sonnet", "opus"]>>;
    description: z.ZodString;
}, "strip", z.ZodTypeAny, {
    name: string;
    context: "test-generation" | "test-execution" | "coverage-analysis" | "quality-assessment" | "defect-intelligence" | "requirements-validation" | "code-intelligence" | "security-compliance" | "contract-testing" | "visual-accessibility" | "chaos-resilience" | "learning-optimization";
    id: string;
    description: string;
    capabilities: string[];
    modelTier: "haiku" | "sonnet" | "opus" | "agent-booster";
}, {
    name: string;
    context: "test-generation" | "test-execution" | "coverage-analysis" | "quality-assessment" | "defect-intelligence" | "requirements-validation" | "code-intelligence" | "security-compliance" | "contract-testing" | "visual-accessibility" | "chaos-resilience" | "learning-optimization";
    id: string;
    description: string;
    capabilities: string[];
    modelTier?: "haiku" | "sonnet" | "opus" | "agent-booster" | undefined;
}>;
/**
 * Generate tests MCP tool input schema
 */
export declare const GenerateTestsInputSchema: z.ZodObject<{
    targetPath: z.ZodString;
    testType: z.ZodDefault<z.ZodEnum<["unit", "integration", "e2e", "property", "mutation", "fuzz", "api", "performance", "security", "accessibility", "contract", "bdd"]>>;
    framework: z.ZodOptional<z.ZodEnum<["vitest", "jest", "mocha", "pytest", "junit", "xunit", "nunit", "playwright", "cypress"]>>;
    coverage: z.ZodOptional<z.ZodObject<{
        target: z.ZodDefault<z.ZodNumber>;
        focusGaps: z.ZodDefault<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        target: number;
        focusGaps: boolean;
    }, {
        target?: number | undefined;
        focusGaps?: boolean | undefined;
    }>>;
    style: z.ZodDefault<z.ZodEnum<["tdd-london", "tdd-chicago", "bdd", "example-based"]>>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    testType: "unit" | "integration" | "e2e" | "property" | "mutation" | "fuzz" | "api" | "performance" | "security" | "accessibility" | "contract" | "bdd";
    style: "bdd" | "tdd-london" | "tdd-chicago" | "example-based";
    framework?: "vitest" | "jest" | "mocha" | "pytest" | "junit" | "xunit" | "nunit" | "playwright" | "cypress" | undefined;
    coverage?: {
        target: number;
        focusGaps: boolean;
    } | undefined;
}, {
    targetPath: string;
    testType?: "unit" | "integration" | "e2e" | "property" | "mutation" | "fuzz" | "api" | "performance" | "security" | "accessibility" | "contract" | "bdd" | undefined;
    framework?: "vitest" | "jest" | "mocha" | "pytest" | "junit" | "xunit" | "nunit" | "playwright" | "cypress" | undefined;
    coverage?: {
        target?: number | undefined;
        focusGaps?: boolean | undefined;
    } | undefined;
    style?: "bdd" | "tdd-london" | "tdd-chicago" | "example-based" | undefined;
}>;
/**
 * Analyze coverage MCP tool input schema
 */
export declare const AnalyzeCoverageInputSchema: z.ZodObject<{
    coverageReport: z.ZodOptional<z.ZodString>;
    targetPath: z.ZodString;
    algorithm: z.ZodDefault<z.ZodEnum<["johnson-lindenstrauss", "full-scan"]>>;
    prioritize: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    algorithm: "johnson-lindenstrauss" | "full-scan";
    prioritize: boolean;
    coverageReport?: string | undefined;
}, {
    targetPath: string;
    coverageReport?: string | undefined;
    algorithm?: "johnson-lindenstrauss" | "full-scan" | undefined;
    prioritize?: boolean | undefined;
}>;
/**
 * Security scan MCP tool input schema
 */
export declare const SecurityScanInputSchema: z.ZodObject<{
    targetPath: z.ZodString;
    scanType: z.ZodDefault<z.ZodEnum<["sast", "dast", "both"]>>;
    compliance: z.ZodDefault<z.ZodArray<z.ZodEnum<["owasp-top-10", "sans-25", "pci-dss", "hipaa", "gdpr", "soc2"]>, "many">>;
    severity: z.ZodDefault<z.ZodEnum<["all", "critical", "high", "medium"]>>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    scanType: "sast" | "dast" | "both";
    compliance: ("owasp-top-10" | "sans-25" | "pci-dss" | "hipaa" | "gdpr" | "soc2")[];
    severity: "critical" | "high" | "medium" | "all";
}, {
    targetPath: string;
    scanType?: "sast" | "dast" | "both" | undefined;
    compliance?: ("owasp-top-10" | "sans-25" | "pci-dss" | "hipaa" | "gdpr" | "soc2")[] | undefined;
    severity?: "critical" | "high" | "medium" | "all" | undefined;
}>;
/**
 * Validate contract MCP tool input schema
 */
export declare const ValidateContractInputSchema: z.ZodObject<{
    contractPath: z.ZodString;
    contractType: z.ZodEnum<["openapi", "graphql", "grpc", "asyncapi"]>;
    targetUrl: z.ZodOptional<z.ZodString>;
    strict: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    strict: boolean;
    contractPath: string;
    contractType: "openapi" | "graphql" | "grpc" | "asyncapi";
    targetUrl?: string | undefined;
}, {
    contractPath: string;
    contractType: "openapi" | "graphql" | "grpc" | "asyncapi";
    strict?: boolean | undefined;
    targetUrl?: string | undefined;
}>;
/**
 * Chaos inject MCP tool input schema
 */
export declare const ChaosInjectInputSchema: z.ZodObject<{
    target: z.ZodString;
    failureType: z.ZodEnum<["network-latency", "network-partition", "cpu-stress", "memory-pressure", "disk-failure", "process-kill"]>;
    duration: z.ZodDefault<z.ZodNumber>;
    intensity: z.ZodDefault<z.ZodNumber>;
    dryRun: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    target: string;
    failureType: "network-latency" | "network-partition" | "cpu-stress" | "memory-pressure" | "disk-failure" | "process-kill";
    duration: number;
    intensity: number;
    dryRun: boolean;
}, {
    target: string;
    failureType: "network-latency" | "network-partition" | "cpu-stress" | "memory-pressure" | "disk-failure" | "process-kill";
    duration?: number | undefined;
    intensity?: number | undefined;
    dryRun?: boolean | undefined;
}>;
/**
 * Evaluate quality gate MCP tool input schema
 */
export declare const EvaluateQualityGateInputSchema: z.ZodObject<{
    gates: z.ZodOptional<z.ZodArray<z.ZodObject<{
        metric: z.ZodString;
        operator: z.ZodEnum<[">", "<", ">=", "<=", "=="]>;
        threshold: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
    }, {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
    }>, "many">>;
    defaults: z.ZodDefault<z.ZodEnum<["strict", "standard", "minimal"]>>;
}, "strip", z.ZodTypeAny, {
    defaults: "strict" | "standard" | "minimal";
    gates?: {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
    }[] | undefined;
}, {
    gates?: {
        metric: string;
        operator: ">" | "<" | ">=" | "<=" | "==";
        threshold: number;
    }[] | undefined;
    defaults?: "strict" | "standard" | "minimal" | undefined;
}>;
/**
 * Predict defects MCP tool input schema
 */
export declare const PredictDefectsInputSchema: z.ZodObject<{
    targetPath: z.ZodString;
    depth: z.ZodDefault<z.ZodEnum<["shallow", "medium", "deep"]>>;
    includeRootCause: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    depth: "medium" | "shallow" | "deep";
    includeRootCause: boolean;
}, {
    targetPath: string;
    depth?: "medium" | "shallow" | "deep" | undefined;
    includeRootCause?: boolean | undefined;
}>;
/**
 * TDD cycle MCP tool input schema
 */
export declare const TDDCycleInputSchema: z.ZodObject<{
    requirement: z.ZodString;
    targetPath: z.ZodString;
    style: z.ZodDefault<z.ZodEnum<["london", "chicago"]>>;
    maxCycles: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    targetPath: string;
    style: "london" | "chicago";
    requirement: string;
    maxCycles: number;
}, {
    targetPath: string;
    requirement: string;
    style?: "london" | "chicago" | undefined;
    maxCycles?: number | undefined;
}>;
export type TestGenerationInput = z.infer<typeof TestGenerationRequestSchema>;
export type TDDCycleInput = z.infer<typeof TDDCycleRequestSchema>;
export type CoverageAnalysisInput = z.infer<typeof CoverageAnalysisRequestSchema>;
export type QualityGateInput = z.infer<typeof QualityGateRequestSchema>;
export type DefectPredictionInput = z.infer<typeof DefectPredictionRequestSchema>;
export type SecurityScanInput = z.infer<typeof SecurityScanRequestSchema>;
export type ContractValidationInput = z.infer<typeof ContractValidationRequestSchema>;
export type ChaosInjectionInput = z.infer<typeof ChaosInjectionRequestSchema>;
export type VisualRegressionInput = z.infer<typeof VisualRegressionRequestSchema>;
export type AccessibilityCheckInput = z.infer<typeof AccessibilityCheckRequestSchema>;
export type PluginConfig = z.infer<typeof PluginConfigSchema>;
export type SandboxConfig = z.infer<typeof SandboxConfigSchema>;
export type ModelRoutingConfig = z.infer<typeof ModelRoutingConfigSchema>;
export type MemoryNamespace = z.infer<typeof MemoryNamespaceSchema>;
export type WorkerDefinition = z.infer<typeof WorkerDefinitionSchema>;
export type HookDefinition = z.infer<typeof HookDefinitionSchema>;
export type AgentDefinition = z.infer<typeof AgentDefinitionSchema>;
/**
 * Validate input against schema with detailed errors
 */
export declare function validateInput<T>(schema: z.ZodSchema<T>, input: unknown): {
    success: true;
    data: T;
} | {
    success: false;
    errors: string[];
};
/**
 * Create a validated request or throw
 */
export declare function parseOrThrow<T>(schema: z.ZodSchema<T>, input: unknown): T;
/**
 * Create a validated request with defaults
 */
export declare function parseWithDefaults<T>(schema: z.ZodSchema<T>, input: unknown): T;
//# sourceMappingURL=schemas.d.ts.map