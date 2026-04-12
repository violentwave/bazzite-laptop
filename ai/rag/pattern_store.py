"""LanceDB store for curated code patterns.

Table: code_patterns

Schema fields:
    id -- SHA256 hash of content (dedup key)
    content -- Full markdown body (frontmatter stripped)
    language -- Programming language (python, rust, javascript,
                typescript, bash, c, yaml)
    domain -- Domain category (security, networking, systems,
              data, web, testing, frontend)
    pattern_type -- Type (pattern, anti_pattern, idiom, recipe)
    title -- Human-readable title
    source -- Origin (curated)
    tags -- Comma-separated tags
    timestamp -- ISO 8601 ingest timestamp
    vector -- 768-dim embedding
    archetype -- Frontend: landing-page, service-site, dashboard,
                 portfolio, lead-gen
    pattern_scope -- Frontend: section, component, layout, motion,
                     asset, token, workflow, media, effect
    semantic_role -- Frontend: hero, cta, navigation, pricing,
                     testimonial, etc.
    generation_priority -- Frontend: 1-10 ranking for generation order
"""

import hashlib
import logging

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger(__name__)

PATTERN_TABLE = "code_patterns"

VALID_LANGUAGES = {"python", "rust", "javascript", "typescript", "bash", "c", "yaml"}
VALID_DOMAINS = {"security", "networking", "systems", "data", "web", "testing", "frontend"}
VALID_TYPES = {"pattern", "anti_pattern", "idiom", "recipe"}

# Frontend-specific validation sets
VALID_ARCHETYPES = {
    "landing-page",
    "service-site",
    "dashboard",
    "portfolio",
    "lead-gen",
}
VALID_PATTERN_SCOPES = {
    "section",
    "component",
    "layout",
    "motion",
    "asset",
    "token",
    "workflow",
    "media",
    "effect",
}
VALID_SEMANTIC_ROLES = {
    "hero",
    "cta",
    "navigation",
    "pricing",
    "testimonial",
    "feature",
    "footer",
    "form",
    "gallery",
    "kpi",
    "chart",
    "modal",
    "card",
    "grid",
    "list",
    "header",
    "sidebar",
    "animation",
    "asset",
    "token",
    "workflow",
    "illustration",
    "background",
    "logo",
    "proof",
    "media",
    "visual-effect",
}

SCHEMA = pa.schema(
    [
        pa.field("id", pa.utf8()),
        pa.field("content", pa.utf8()),
        pa.field("language", pa.utf8()),
        pa.field("domain", pa.utf8()),
        pa.field("pattern_type", pa.utf8()),
        pa.field("title", pa.utf8()),
        pa.field("source", pa.utf8()),
        pa.field("tags", pa.utf8()),
        pa.field("timestamp", pa.utf8()),
        pa.field("vector", pa.list_(pa.float32(), 768)),
        pa.field("archetype", pa.utf8()),
        pa.field("pattern_scope", pa.utf8()),
        pa.field("semantic_role", pa.utf8()),
        pa.field("generation_priority", pa.int32()),
    ]
)

_db = None


def _get_db():
    """Get or create the LanceDB connection."""
    global _db
    if _db is None:
        VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
        _db = lancedb.connect(str(VECTOR_DB_DIR))
    return _db


def get_or_create_table() -> lancedb.table.Table:
    """Open the code_patterns table, creating it with SCHEMA if it doesn't exist."""
    db = _get_db()
    try:
        tables = db.list_tables()
        existing = tables.tables if hasattr(tables, "tables") else list(tables)
        if PATTERN_TABLE in existing:
            return db.open_table(PATTERN_TABLE)
    except Exception as e:
        logger.debug(f"Error checking existing tables: {e}")

    try:
        return db.create_table(PATTERN_TABLE, schema=SCHEMA)
    except Exception as e:
        if "already exists" in str(e).lower():
            return db.open_table(PATTERN_TABLE)
        raise


def content_id(content: str) -> str:
    """Generate a deterministic SHA256 hex digest for content (dedup key)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def upsert_pattern(record: dict) -> None:
    """Add a pattern record to the code_patterns table.

    Validates required keys and skips if id already exists.
    Frontend metadata (archetype, pattern_scope, semantic_role,
    generation_priority) are optional.
    """
    required_keys = {
        "id",
        "content",
        "language",
        "domain",
        "pattern_type",
        "title",
        "source",
        "tags",
        "timestamp",
        "vector",
    }
    missing = required_keys - set(record.keys())
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    if record["language"] not in VALID_LANGUAGES:
        raise ValueError(
            f"Invalid language: {record['language']!r}. Valid: {sorted(VALID_LANGUAGES)}"
        )
    if record["domain"] not in VALID_DOMAINS:
        raise ValueError(f"Invalid domain: {record['domain']!r}. Valid: {sorted(VALID_DOMAINS)}")
    if record["pattern_type"] not in VALID_TYPES:
        raise ValueError(
            f"Invalid pattern_type: {record['pattern_type']!r}. Valid: {sorted(VALID_TYPES)}"
        )

    # Validate optional frontend metadata if present
    if record.get("archetype") and record["archetype"] not in VALID_ARCHETYPES:
        raise ValueError(
            f"Invalid archetype: {record['archetype']!r}. Valid: {sorted(VALID_ARCHETYPES)}"
        )
    if record.get("pattern_scope") and record["pattern_scope"] not in VALID_PATTERN_SCOPES:
        valid_scopes = sorted(VALID_PATTERN_SCOPES)
        raise ValueError(
            f"Invalid pattern_scope: {record['pattern_scope']!r}. Valid: {valid_scopes}"
        )
    if record.get("semantic_role") and record["semantic_role"] not in VALID_SEMANTIC_ROLES:
        valid_roles = sorted(VALID_SEMANTIC_ROLES)
        raise ValueError(
            f"Invalid semantic_role: {record['semantic_role']!r}. Valid: {valid_roles}"
        )
    if record.get("generation_priority") is not None:
        priority = record["generation_priority"]
        if not isinstance(priority, int) or priority < 1 or priority > 10:
            raise ValueError(f"Invalid generation_priority: {priority!r}. Must be an integer 1-10.")

    table = get_or_create_table()

    try:
        existing_df = table.to_pandas()
        existing_ids = set(existing_df["id"].tolist()) if "id" in existing_df.columns else set()
    except Exception:
        existing_ids = set()

    if record["id"] in existing_ids:
        return

    table.add([record])


def table_stats() -> dict:
    """Return stats for the code_patterns table."""
    try:
        table = get_or_create_table()
        count = table.count_rows()
        return {"table": PATTERN_TABLE, "rows": count, "size_bytes": 0}
    except Exception:
        return {"table": PATTERN_TABLE, "rows": 0, "size_bytes": 0}
