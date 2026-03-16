"""AI-powered fix suggestion generator for lint findings.

Takes lint findings, reads surrounding source code, and generates
fix suggestions via the LLM router (fast tier).
"""

import logging
from pathlib import Path

from ai.code_quality.models import LintFinding, LintSummary, Severity
from ai.config import APP_NAME
from ai.rate_limiter import RateLimiter
from ai.router import route_query

logger = logging.getLogger(APP_NAME)

# Only suggest fixes for ERROR and WARNING severity
_FIXABLE_SEVERITIES = {Severity.ERROR, Severity.WARNING}

# Max findings to send to LLM (avoid rate limit exhaustion)
MAX_FIX_SUGGESTIONS = 10

# Lines of context around the finding to include in the prompt
CONTEXT_LINES = 5


def analyze_findings(
    summaries: list[LintSummary],
    rate_limiter: RateLimiter | None = None,
    max_suggestions: int = MAX_FIX_SUGGESTIONS,
) -> list[LintSummary]:
    """Enrich lint findings with AI fix suggestions.

    Modifies findings in-place by setting fix_suggestion on fixable items.
    Only processes ERROR and WARNING severity findings, up to max_suggestions.

    Args:
        summaries: List of LintSummary from runner.
        rate_limiter: Optional rate limiter for LLM calls.
        max_suggestions: Max number of findings to generate fixes for.

    Returns:
        The same list of summaries (modified in-place).
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()

    # Collect fixable findings across all summaries
    fixable: list[LintFinding] = []
    for summary in summaries:
        for finding in summary.findings:
            if finding.severity in _FIXABLE_SEVERITIES:
                fixable.append(finding)

    # Limit to max_suggestions (prioritize errors first)
    fixable.sort(key=lambda f: (f.severity != Severity.ERROR, f.file, f.line))
    fixable = fixable[:max_suggestions]

    if not fixable:
        logger.info("No fixable findings to analyze")
        return summaries

    logger.info("Generating AI fix suggestions for %d findings", len(fixable))

    for finding in fixable:
        try:
            suggestion = _generate_fix(finding, rate_limiter)
            if suggestion:
                finding.fix_suggestion = suggestion
        except Exception:
            logger.exception(
                "Failed to generate fix for %s:%d [%s]",
                finding.file, finding.line, finding.code,
            )

    return summaries


def _generate_fix(finding: LintFinding, rate_limiter: RateLimiter) -> str:
    """Generate a fix suggestion for a single finding.

    Reads source context around the finding line, builds a prompt,
    and routes to the fast LLM tier.

    Returns empty string if source can't be read or LLM fails.
    """
    source_context = _read_source_context(finding.file, finding.line)

    prompt = _build_fix_prompt(finding, source_context)

    try:
        response = route_query("fast", prompt)
        # If router returns scaffold, return empty
        if "[SCAFFOLD]" in response:
            return ""
        return response.strip()
    except (RuntimeError, ValueError) as exc:
        logger.debug("LLM fix suggestion failed: %s", exc)
        return ""


def _read_source_context(file_path: str, line: int) -> str:
    """Read lines around the finding for LLM context."""
    try:
        path = Path(file_path)
        if not path.is_file():
            return ""
        lines = path.read_text().splitlines()
        start = max(0, line - CONTEXT_LINES - 1)
        end = min(len(lines), line + CONTEXT_LINES)
        numbered = [
            f"{i + 1:4d} | {lines[i]}" for i in range(start, end)
        ]
        return "\n".join(numbered)
    except (OSError, UnicodeDecodeError):
        return ""


def _build_fix_prompt(finding: LintFinding, source_context: str) -> str:
    """Build the LLM prompt for generating a fix suggestion."""
    return (
        f"You are a code quality assistant. Fix the following lint finding.\n\n"
        f"Tool: {finding.tool}\n"
        f"Rule: {finding.code}\n"
        f"Message: {finding.message}\n"
        f"File: {finding.file}:{finding.line}\n"
        f"Severity: {finding.severity.value}\n\n"
        f"Source context:\n```\n{source_context}\n```\n\n"
        f"Provide ONLY the corrected code snippet. No explanation needed."
    )
