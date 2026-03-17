/**
 * Economy Bridge - Financial Risk Plugin
 *
 * Provides token economics and portfolio risk calculation
 * capabilities. Integrates with ruvector-economy-wasm for
 * high-performance VaR, CVaR, and Monte Carlo simulations.
 *
 * Compliance Features:
 * - Deterministic execution for audit reproducibility
 * - Calculation proofs for regulatory requirements
 * - Rate limiting to prevent abuse
 */
import type { EconomyBridge, EconomyConfig, PortfolioHolding, RiskMetrics, TimeHorizon, RiskCalculationProof, Logger } from '../types.js';
/**
 * Portfolio risk calculator with pure JavaScript fallback
 */
export declare class PortfolioRiskCalculator {
    /**
     * Calculate Value at Risk (VaR) using historical simulation
     */
    calculateVaR(returns: number[], confidenceLevel?: number): number;
    /**
     * Calculate Conditional VaR (CVaR / Expected Shortfall)
     */
    calculateCVaR(returns: number[], confidenceLevel?: number): number;
    /**
     * Calculate annualized volatility
     */
    calculateVolatility(returns: number[], annualizationFactor?: number): number;
    /**
     * Calculate Sharpe Ratio
     */
    calculateSharpe(returns: number[], riskFreeRate?: number): number;
    /**
     * Calculate Sortino Ratio
     */
    calculateSortino(returns: number[], riskFreeRate?: number): number;
    /**
     * Calculate Maximum Drawdown
     */
    calculateMaxDrawdown(prices: number[]): number;
    /**
     * Calculate Beta against market benchmark
     */
    calculateBeta(assetReturns: number[], marketReturns: number[]): number;
    /**
     * Monte Carlo simulation for portfolio
     */
    monteCarloSimulation(portfolioReturns: number[], scenarios?: number, horizon?: number, seed?: number): number[];
    private calculateAnnualizedReturn;
    private seededRandom;
}
/**
 * Financial Economy Bridge implementation
 */
export declare class FinancialEconomyBridge implements EconomyBridge {
    private wasmModule;
    private config;
    private logger;
    private calculator;
    private marketDataCache;
    private randomSeed;
    initialized: boolean;
    constructor(config?: Partial<EconomyConfig>, logger?: Logger);
    /**
     * Initialize the economy bridge
     */
    initialize(config?: EconomyConfig): Promise<void>;
    /**
     * Calculate Value at Risk
     */
    calculateVar(returns: Float32Array, confidence: number): Promise<number>;
    /**
     * Calculate Conditional VaR
     */
    calculateCvar(returns: Float32Array, confidence: number): Promise<number>;
    /**
     * Optimize portfolio allocation
     */
    optimizePortfolio(returns: Float32Array[], constraints: Record<string, number>): Promise<Float32Array>;
    /**
     * Run Monte Carlo simulation
     */
    simulateMonteCarlo(portfolio: Float32Array, scenarios: number, horizon: number): Promise<Float32Array>;
    /**
     * Calculate complete risk metrics for a portfolio
     */
    calculateRiskMetrics(holdings: PortfolioHolding[], confidenceLevel?: number, horizon?: TimeHorizon): Promise<RiskMetrics>;
    /**
     * Generate calculation proof for audit
     */
    generateCalculationProof(input: unknown, output: unknown, _modelVersion?: string): RiskCalculationProof;
    /**
     * Cleanup resources
     */
    destroy(): void;
    private resolveWasmPath;
    private loadWasmModule;
    private generateSyntheticReturns;
    private returnsToPrice;
    private getHorizonDays;
    private scaleReturns;
    private hashObject;
    private getModelChecksum;
    private signProof;
}
/**
 * Create a new economy bridge instance
 */
export declare function createEconomyBridge(config?: Partial<EconomyConfig>, logger?: Logger): FinancialEconomyBridge;
export default FinancialEconomyBridge;
//# sourceMappingURL=economy-bridge.d.ts.map