# Bazzite Memory Skill Bundle

Tools for searching conversation memories stored by the AI assistant across
sessions. Memory entries capture important decisions, preferences, and context
from prior interactions.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `memory.search` | Search conversation memories by semantic similarity | `query` (string, required), `top_k` (optional, default 5) |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "What did we decide about the scan schedule?" | `memory.search` with `query="scan schedule decision"` |
| "Do you remember what we said about the GPU?" | `memory.search` with `query="GPU configuration"` |
| "Search your memory for anything about LanceDB" | `memory.search` with `query="LanceDB"` |
| "What was the reason we disabled X?" | `memory.search` with `query="disabled X reason"` |
| "Show me 10 memories about security" | `memory.search` with `query="security", top_k=10` |

---

## Safety Rules

- `memory.search` is read-only. It returns stored memory snippets ranked by
  relevance to the query.
- Memory entries reflect what the AI assistant recorded in prior sessions.
  They may be incomplete or outdated — always verify against current system
  state before acting on a recalled decision.
- Results are truncated to 4 KB. Use a more specific query if results are noisy.
