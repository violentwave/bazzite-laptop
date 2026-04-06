---
name: bazzite-test-analyzer
description: Analyzes pytest test failures in bazzite-laptop, identifies root causes, suggests fixes, and tracks failure patterns over time
compatibility: Created for Zo Computer - Python 3.12+ with junitparser
metadata:
  author: topoman.zo.computer
  version: "1.0.0"
  created: 2026-04-06
---

# Bazzite Test Failure Analyzer

Intelligent analysis of the ~1951 pytest tests in bazzite-laptop. Parses JUnit XML output, identifies failure patterns, suggests fixes using LLM, and tracks historical trends.

## What It Does

1. **Parse Test Results** - Reads pytest JUnit XML output
2. **Categorize Failures** - Groups by error type (assertion, import, timeout, mock, etc.)
3. **Pattern Detection** - Identifies recurring failures across runs
4. **Code Context** - Extracts relevant source lines for failing tests
5. **LLM Analysis** - Sends failure context to your router for fix suggestions
6. **Trend Tracking** - Saves historical data to detect regression patterns
7. **Report Generation** - Creates actionable fix recommendations

## Integration with Bazzite System

- Reads from your existing test infrastructure (`tests/` directory)
- Integrates with `ai/router.py` for LLM-powered fix suggestions
- Saves to `~/security/intel/tests/` for pattern analysis
- Updates HANDOFF.md with critical test failures
- Alerts on test regression (more failures than last run)

## Usage

### After Test Run
```bash
cd ~/workspace/Skills/bazzite-test-analyzer
./scripts/analyze.sh ~/path/to/bazzite-laptop/junit.xml
```

### With Pytest (One-liner)
```bash
cd ~/bazzite-laptop
pytest --junitxml=results.xml -x && \
  analyze-tests results.xml
```

## Output Format

```json
{
  "run_id": "2026-04-06_143022",
  "total_tests": 1951,
  "passed": 1948,
  "failed": 3,
  "categories": {
    "assertion_error": 2,
    "timeout_error": 1
  },
  "failures": [
    {
      "test": "test_threat_intel.py::test_virustotal_rate_limit",
      "error": "assert 429 == 200",
      "category": "assertion_error",
      "suggestion": "Mock the rate limit response in test",
      "llm_analysis": "..."
    }
  ]
}
```

## Files
- `scripts/analyze.py` - Main analyzer
- `scripts/analyze.sh` - Wrapper script
- `references/fix_templates.md` - Common fix patterns