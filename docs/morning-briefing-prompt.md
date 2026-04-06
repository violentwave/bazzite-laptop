# Morning Briefing Prompt — Bazzite Gaming Laptop
<!-- Paste into Newelle as a scheduled task (daily ~08:30) -->
<!-- Last updated: 2026-03-31 -->

```
Good morning. Run my daily system briefing. Call ALL of the following tools
in a single batch — do not call them one at a time:

  1. security.status
  2. security.last_scan
  3. security.health_snapshot
  4. security.threat_summary
  5. logs.anomalies
  6. system.release_watch
  7. system.fedora_updates
  8. system.budget_status
  9. system.metrics_summary
 10. system.provider_status
 11. agents.timer_health
 12. system.dep_audit

After all twelve respond, give me a concise morning briefing covering:

SECURITY:
- Overall threat status from security.threat_summary (overall_status field)
- CVE highlights: high-severity count, any KEV-listed CVEs
- Audit status and any flags from the RAG summary
- Last ClamAV scan result and when it ran
- Any unacknowledged anomalies from logs.anomalies

HEALTH:
- System health status from security.status
- Any open health issues
- Most recent health snapshot summary
- All timers firing correctly (agents.timer_health); flag any missed or overdue

UPDATES:
- Any new upstream releases from system.release_watch (new versions, GHSA advisories)
- Any pending Fedora/Bazzite security updates from system.fedora_updates
- Any vulnerable dependencies from system.dep_audit (package name + CVE if present)

BUDGET & PROVIDERS:
- Token budget remaining today (system.budget_status) — warn if any tier below 20%
- LLM provider health (system.provider_status) — flag any degraded or failing providers
- Cache and latency summary from system.metrics_summary

ACTION ITEMS (only list if applicable):
- Any KEV CVEs → recommend immediate patching
- Any "issues" or "critical" overall_status → name the source and describe the issue
- Any anomalies requiring attention → name and suggest next step
- Any GHSA security advisories → name the package and severity
- Any critical Fedora security updates → name and recommend: security.run_ingest to re-index
- If no threat_summary data yet → suggest running: security.cve_check
- Any timer not fired in expected window → name the timer and its last run time
- Any provider error rate >10% → name it and suggest switching task type

Format: 3-4 short bullet points per section. Lead with the most urgent item.
If everything is clean, say so in one sentence and stop.
Do NOT repeat raw JSON. Translate tool output into plain English.
```
