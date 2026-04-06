#!/usr/bin/env python3
"""
Ingest scraped intelligence into LanceDB RAG for bazzite-laptop system.

Reads from ~/security/intel/ingest/pending_ingest.jsonl and adds to the
'knowledge_ingest' table for later embedding + RAG search.

Usage:
    python3 ingest_to_rag.py [--auto-embed]
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

INTEL_DIR = Path.home() / "security" / "intel"
INGEST_FILE = INTEL_DIR / "ingest" / "pending_ingest.jsonl"
PROCESSED_FILE = INTEL_DIR / "ingest" / "processed_ingest.jsonl"

# Add path to ai.rag module if running from skill
sys.path.insert(0, str(Path.home() / "bazzite-laptop"))


def ingest_pending() -> dict:
    """Read pending ingest file and add to RAG store."""
    if not INGEST_FILE.exists():
        return {"status": "no_data", "count": 0}

    # Read pending items
    items = []
    with open(INGEST_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if not items:
        return {"status": "empty", "count": 0}

    # Try to import and use the RAG store
    try:
        from ai.rag.store import get_store
        store = get_store()

        # Add to knowledge_ingest table (or create if needed)
        ingest_records = []
        for item in items:
            record = {
                "id": f"{item['source']}_{item['scraped_at']}",
                "source": item["source"],
                "scraped_at": item["scraped_at"],
                "text": item["text"],
                "metadata": item["data"],
                "type": "intelligence",
            }
            ingest_records.append(record)

        # Insert into LanceDB
        table = store.get_or_create_table("knowledge_ingest", schema=store.SCHEMAS["documents"])
        table.add(ingest_records)

        # Mark as processed
        with open(PROCESSED_FILE, "a") as f:
            for item in items:
                f.write(json.dumps({
                    **item,
                    "processed_at": datetime.now(UTC).isoformat(),
                }) + "\n")

        # Clear pending
        INGEST_FILE.unlink()

        return {
            "status": "success",
            "count": len(items),
            "sources": list(set(i["source"] for i in items)),
        }

    except ImportError as e:
        # If ai.rag not available, just keep in JSONL format
        # The rag-embed.timer will pick it up
        return {
            "status": "deferred",
            "count": len(items),
            "message": f"ai.rag not available ({e}), keeping for rag-embed.timer",
        }

    except Exception as e:
        return {
            "status": "error",
            "count": 0,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-embed", action="store_true", help="Trigger embedding after ingest")
    args = parser.parse_args()

    result = ingest_pending()
    print(json.dumps(result, indent=2))

    if args.auto_embed and result["status"] in ("success", "deferred"):
        print("\nTo embed new items, run: ai-rag-ingest or trigger rag-embed.timer")


if __name__ == "__main__":
    main()
