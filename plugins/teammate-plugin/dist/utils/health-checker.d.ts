/**
 * Health Checker for TeammateTool teammates
 *
 * Monitors teammate health status with configurable
 * thresholds and automatic status transitions.
 *
 * @module @claude-flow/teammate-plugin/utils/health-checker
 */
import type { HealthCheckConfig, TeammateHealthCheck, TeamHealthReport } from '../types.js';
/**
 * Health checker with configurable check intervals and thresholds
 */
export declare class HealthChecker {
    private config;
    private onStatusChange?;
    private checks;
    private intervals;
    constructor(config: HealthCheckConfig, onStatusChange?: ((check: TeammateHealthCheck) => void) | undefined);
    /**
     * Start health checks for a teammate
     */
    startChecking(teammateId: string, teamName: string, checkFn: () => Promise<boolean>): void;
    /**
     * Stop health checks for a teammate
     */
    stopChecking(teammateId: string): void;
    /**
     * Perform a single health check
     */
    private performCheck;
    /**
     * Get health check for a teammate
     */
    getCheck(teammateId: string): TeammateHealthCheck | undefined;
    /**
     * Get team health report
     */
    getTeamReport(teamName: string): TeamHealthReport;
    /**
     * Stop all health checks
     */
    stopAll(): void;
    /**
     * Get all checks (for testing)
     */
    getAllChecks(): Map<string, TeammateHealthCheck>;
    /**
     * Force a check immediately (for testing)
     */
    forceCheck(teammateId: string, checkFn: () => Promise<boolean>): Promise<void>;
}
//# sourceMappingURL=health-checker.d.ts.map