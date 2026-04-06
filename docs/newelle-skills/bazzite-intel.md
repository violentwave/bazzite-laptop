# Bazzite Intel Skill Bundle

Tools for triggering intelligence scrapes and ingesting the results into the
RAG knowledge base. These tools feed the security pipeline with fresh CVE,
CISA KEV, GitHub release, and package advisory data.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `intel.scrape_now` | Trigger an intelligence scrape: GitHub releases, CISA KEV, NVD CVEs, package advisories | none |
| `intel.ingest_pending` | Ingest pending scraped intelligence into LanceDB RAG knowledge base | none |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "Fetch the latest CVE data" | `intel.scrape_now` |
| "Run a fresh threat intelligence scrape" | `intel.scrape_now` |
| "Ingest the pending intel into the knowledge base" | `intel.ingest_pending` |
| "Update the RAG database with new advisories" | `intel.ingest_pending` |
| "Get fresh CVE and CISA KEV data, then ingest it" | `intel.scrape_now` then `intel.ingest_pending` |

---

## Typical Workflow

1. `intel.scrape_now` — fetches new data from GitHub Releases, CISA KEV, NVD,
   and package advisory feeds. Returns a summary of what was scraped.
2. `intel.ingest_pending` — takes the scraped data and ingests it into LanceDB
   so it becomes searchable via `knowledge.rag_query` and `security.cve_check`.

Run both in sequence when the user wants fully up-to-date threat intelligence.

---

## Safety Rules

- Both tools run as background systemd jobs. They return quickly with a
  "triggered" confirmation — the actual scrape/ingest continues in the background.
- Do NOT call `intel.scrape_now` more than once per hour — the upstream APIs
  have rate limits. The tool returns an error if called too frequently.
- `intel.ingest_pending` is a no-op if there is nothing new to ingest. It is
  safe to call repeatedly.
- Neither tool modifies the system outside `~/security/` and the LanceDB store.
