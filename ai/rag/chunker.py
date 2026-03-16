"""Section-based log chunker for ClamAV scans and health snapshots.

Splits log files into semantically meaningful sections for embedding.
Each section becomes one vector in the LanceDB store.

Section delimiters:
    Scan logs:   "----------- <TITLE> -----------"
    Health logs:  "--- <TITLE> ---" or "=== <TITLE> ==="
    Detections:   Lines ending with " FOUND" are grouped as "detections"
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

# ── Section delimiter patterns ──

_SCAN_DELIM = re.compile(r"^-{3,}\s+(.+?)\s+-{3,}$")
_HEALTH_DELIM_DASH = re.compile(r"^-{3}\s+(.+?)\s+-{3}$")
_HEALTH_DELIM_EQUALS = re.compile(r"^={3}\s+(.+?)\s+={3}$")
_FOUND_LINE = re.compile(r".+\sFOUND$")
_SCAN_TIMESTAMP = re.compile(r"^Start Date:\s*(.+)$", re.MULTILINE)
_HEALTH_TIMESTAMP = re.compile(r"^Date:\s*(.+)$", re.MULTILINE)


@dataclass
class LogChunk:
    """A single semantically meaningful section extracted from a log file."""

    section: str
    content: str
    log_type: str
    source_file: str
    timestamp: str


def _extract_timestamp(text: str, pattern: re.Pattern[str]) -> str:
    """Extract a timestamp string from text using the given regex pattern."""
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return ""


def chunk_scan_log(text: str, source_file: str = "") -> list[LogChunk]:
    """Parse a ClamAV scan log into sections.

    Sections detected:
    - SCAN SUMMARY (the stats block)
    - detections (all lines with FOUND)
    - Any other delimiter-separated sections

    Extracts timestamp from "Start Date:" line if present.
    """
    timestamp = _extract_timestamp(text, _SCAN_TIMESTAMP)
    chunks: list[LogChunk] = []

    # Collect FOUND lines into a detections section
    found_lines = [line for line in text.splitlines() if _FOUND_LINE.match(line)]
    if found_lines:
        chunks.append(LogChunk(
            section="detections",
            content="\n".join(found_lines),
            log_type="scan",
            source_file=source_file,
            timestamp=timestamp,
        ))

    # Split by delimiter sections
    lines = text.splitlines()
    current_section: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = _SCAN_DELIM.match(line)
        if match:
            # Flush previous section
            if current_section is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append(LogChunk(
                        section=current_section,
                        content=content,
                        log_type="scan",
                        source_file=source_file,
                        timestamp=timestamp,
                    ))
            current_section = match.group(1).strip()
            current_lines = []
        elif current_section is not None:
            # Skip FOUND lines from delimiter sections (already in detections)
            if not _FOUND_LINE.match(line):
                current_lines.append(line)

    # Flush last section
    if current_section is not None:
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(LogChunk(
                section=current_section,
                content=content,
                log_type="scan",
                source_file=source_file,
                timestamp=timestamp,
            ))

    return chunks


def chunk_health_log(text: str, source_file: str = "") -> list[LogChunk]:
    """Parse a system health snapshot into sections.

    Sections detected by "--- Title ---" or "=== Title ===" delimiters.
    Extracts timestamp from "Date:" line in the header.
    """
    timestamp = _extract_timestamp(text, _HEALTH_TIMESTAMP)
    chunks: list[LogChunk] = []

    lines = text.splitlines()
    current_section: str | None = None
    current_lines: list[str] = []

    for line in lines:
        dash_match = _HEALTH_DELIM_DASH.match(line)
        equals_match = _HEALTH_DELIM_EQUALS.match(line)
        match = dash_match or equals_match

        if match:
            # Flush previous section
            if current_section is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append(LogChunk(
                        section=current_section,
                        content=content,
                        log_type="health",
                        source_file=source_file,
                        timestamp=timestamp,
                    ))
            current_section = match.group(1).strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    # Flush last section
    if current_section is not None:
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(LogChunk(
                section=current_section,
                content=content,
                log_type="health",
                source_file=source_file,
                timestamp=timestamp,
            ))

    return chunks


def chunk_file(path: Path) -> list[LogChunk]:
    """Auto-detect log type and chunk a file.

    Detection logic:
    - Files in /var/log/clamav-scans/ or containing "SCAN SUMMARY" -> scan
    - Files in /var/log/system-health/ or containing "System Health" -> health
    - Falls back to single-chunk with section="full" if unknown

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    source = str(path)

    # Detect by path
    if "/clamav-scans/" in source:
        return chunk_scan_log(text, source)
    if "/system-health/" in source:
        return chunk_health_log(text, source)

    # Detect by content
    if "SCAN SUMMARY" in text:
        return chunk_scan_log(text, source)
    if "System Health" in text:
        return chunk_health_log(text, source)

    # Fallback: single chunk
    logger.info("Unknown log type for %s, returning single chunk", source)
    return [LogChunk(
        section="full",
        content=text.strip(),
        log_type="unknown",
        source_file=source,
        timestamp="",
    )] if text.strip() else []


def chunk_enriched_jsonl(path: Path) -> list[dict]:
    """Parse the enriched threat intel JSONL into dicts ready for embedding.

    Each line becomes one dict with keys:
    - id: generated UUID
    - hash, source, family, risk_level from the JSONL
    - content: human-readable summary for embedding
    - timestamp: from the JSONL
    - vector: empty list (filled by embedder later)

    Malformed lines are skipped with a warning.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    results: list[dict] = []
    for line_num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed JSONL line %d in %s", line_num, path)
            continue

        hash_val = data.get("hash", "")
        source = data.get("source", "")
        family = data.get("family", "")
        risk_level = data.get("risk_level", "unknown")
        timestamp = data.get("timestamp", "")

        hash_preview = hash_val[:16] + "..." if len(hash_val) > 16 else hash_val
        content = f"{source}: {family} ({risk_level}) — {hash_preview}"

        results.append({
            "id": str(uuid.uuid4()),
            "hash": hash_val,
            "source": source,
            "family": family,
            "risk_level": risk_level,
            "content": content,
            "timestamp": timestamp,
            "vector": [],
        })

    return results
