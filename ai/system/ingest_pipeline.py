#!/usr/bin/env python3
"""Ingest pipeline for scraped intelligence into LanceDB RAG.

Reads from ~/security/intel/ingest/pending_ingest.jsonl and adds to the
'knowledge_ingest' table for later embedding + RAG search.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def get_intel_dir() -> Path:
    """Get the intel directory path at runtime."""
    return Path.home() / "security" / "intel"


def get_ingest_file(intel_dir: Path | None = None) -> Path:
    """Get the pending ingest file path."""
    if intel_dir is None:
        intel_dir = get_intel_dir()
    return intel_dir / "ingest" / "pending_ingest.jsonl"


def get_processed_file(intel_dir: Path | None = None) -> Path:
    """Get the processed ingest file path."""
    if intel_dir is None:
        intel_dir = get_intel_dir()
    return intel_dir / "ingest" / "processed_ingest.jsonl"


def ingest_intel_to_rag(intel_dir: str | None = None) -> dict[str, Any]:
    """Read pending ingest file and add to RAG store.

    Args:
        intel_dir: Optional path to intel directory (defaults to ~/security/intel)

    Returns:
        dict with status and summary data
    """
    if intel_dir is None:
        intel_dir_path = get_intel_dir()
    else:
        intel_dir_path = Path(intel_dir)

    ingest_file = get_ingest_file(intel_dir_path)
    processed_file = get_processed_file(intel_dir_path)

    if not ingest_file.exists():
        return {"status": "no_data", "count": 0}

    intel_dir_path.mkdir(parents=True, exist_ok=True)
    ingest_file.parent.mkdir(parents=True, exist_ok=True)

    items = []
    with open(ingest_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if not items:
        return {"status": "empty", "count": 0}

    try:
        from ai.rag.store import get_store

        store = get_store()

        ingest_records = []
        for item in items:
            record = {
                "id": f"{item['source']}_{item['scraped_at']}",
                "source": item["source"],
                "scraped_at": item["scraped_at"],
                "text": item["text"],
                "metadata": item.get("data", {}),
                "type": "intelligence",
            }
            ingest_records.append(record)

        table = store.get_or_create_table(
            "knowledge_ingest",
            schema={
                "id": "string",
                "source": "string",
                "scraped_at": "string",
                "text": "string",
                "metadata": "string",
                "type": "string",
            },
        )
        table.add(ingest_records)

        processed_records = []
        for item in items:
            processed_records.append(
                {
                    **item,
                    "processed_at": datetime.now(UTC).isoformat(),
                }
            )

        tmp_processed = processed_file.with_suffix(".tmp")
        with open(tmp_processed, "w") as f:
            for record in processed_records:
                f.write(json.dumps(record) + "\n")
        os.replace(tmp_processed, processed_file)

        ingest_file.unlink()

        return {
            "status": "success",
            "count": len(items),
            "sources": list(set(i.get("source", "unknown") for i in items)),
        }

    except ImportError:
        return {
            "status": "deferred",
            "count": len(items),
            "message": "ai.rag not available, keeping for rag-embed.timer",
        }

    except Exception as e:
        return {
            "status": "error",
            "count": 0,
            "error": str(e),
        }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--intel-dir",
        help="Path to intel directory (default: ~/security/intel)",
    )
    parser.add_argument(
        "--auto-embed",
        action="store_true",
        help="Trigger embedding after ingest",
    )
    args = parser.parse_args()

    result = ingest_intel_to_rag(args.intel_dir)
    print(json.dumps(result, indent=2))

    if args.auto_embed and result["status"] in ("success", "deferred"):
        print("\nTo embed new items, run: ai-rag-ingest or trigger rag-embed.timer")


if __name__ == "__main__":
    main()
