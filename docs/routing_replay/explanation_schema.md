# P131 Explanation Schema

Replay explanations are JSON objects with stable keys and deterministic ordering.

```json
{
  "fixture_id": "string",
  "title": "string",
  "requested_task_type": "fast|reason|batch|code|embed",
  "task_chain": ["string"],
  "source": "string (redacted)",
  "prompt": "string (redacted)",
  "available_candidates": [
    {
      "provider": "string",
      "model": "string",
      "task_types": ["string"],
      "latency_ms": "number",
      "estimated_cost_usd": "number",
      "health": {
        "provider": "string",
        "score": "number",
        "effective_score": "number",
        "auth_broken": "boolean",
        "disabled": "boolean",
        "stale_seconds": "number|null"
      },
      "score": "number",
      "accepted": "boolean",
      "reasons": ["string"]
    }
  ],
  "provider_health_inputs": ["health objects"],
  "budget_constraints": {
    "applied": "boolean",
    "allowed": "boolean",
    "reason": "string",
    "state": "string"
  },
  "failover_conditions": ["provider id"],
  "selected_route": {
    "provider": "string",
    "model": "string",
    "score": "number"
  },
  "rejected_routes": [
    {
      "provider": "string",
      "reason": "comma separated reasons"
    }
  ],
  "reason_summary": "string"
}
```

Security and privacy notes:

- Fixture load fails if secret-like patterns or sensitive local paths are detected.
- Prompts and source labels are redacted before inclusion in outputs.
