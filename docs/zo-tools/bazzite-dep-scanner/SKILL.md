---
name: bazzite-dep-scanner
description: Automated dependency vulnerability scanner for bazzite-laptop - scans pip/npm packages against CVE database and OSV, integrates with threat intel system
compatibility: Created for Zo Computer - Python 3.12+ with httpx, packaging
metadata:
  author: topoman.zo.computer
  version: "1.0.0"
  created: 2026-04-06
---

# Bazzite Dependency Vulnerability Scanner

Scans Python (requirements.txt, pyproject.toml) and Node.js (package.json, package-lock.json) dependencies for known vulnerabilities, integrating with your existing threat intel pipeline.

## What It Does

1. **Parse Dependencies** - Reads requirements.txt, pyproject.toml, package.json
2. **OSV API Lookup** - Queries Open Source Vulnerabilities database
3. **GitHub Advisory** - Secondary check against GH Security Advisories
4. **Cross-Reference** - Matches against your CISA KEV feed
5. **Risk Scoring** - CVSS + exploit availability + your system relevance
6. **Auto-Alert** - High-risk CVEs trigger your MCP alert system

## Integration with Bazzite System

- Saves results to `~/security/intel/dependencies/` 
- Feeds into your LanceDB `vulnerabilities` table
- Triggers alerts via your existing `ai/mcp_bridge/tools.py` alert endpoint
- Updates HANDOFF.md with remediation tasks

## Usage

### Manual Scan
```bash
cd ~/workspace/Skills/bazzite-dep-scanner
./scripts/scan.sh /path/to/bazzite-laptop/repo
```

### Scheduled (Daily at 6 AM)
Runs automatically to catch new CVEs for your pinned dependencies.

## Output Format

```json
{
  "scan_time": "2026-04-06T10:00:00Z",
  "package": "litellm",
  "installed": "1.60.0",
  "vulnerabilities": [
    {
      "cve_id": "CVE-2025-xxxxx",
      "severity": "HIGH",
      "cvss_score": 7.5,
      "fixed_in": "1.61.2",
      "kev": true,
      "recommendation": "Upgrade to 1.61.2"
    }
  ]
}
```

## Files
- `scripts/scan.py` - Main scanner
- `scripts/scan.sh` - Wrapper script