"""Atomic JSONL scan storage used by the standalone MCP server."""

import asyncio
import json
import os
import threading
import uuid
from pathlib import Path

_DEFAULT_SCAN_DIR = Path(__file__).resolve().parents[2] / "data" / "scans"
_SCAN_DIR_SETTING = os.environ.get("SCANME_MCP_SCAN_DIR")
SCAN_DIR = Path(_SCAN_DIR_SETTING).expanduser() if _SCAN_DIR_SETTING else _DEFAULT_SCAN_DIR
SCAN_DIR.mkdir(parents=True, exist_ok=True)

_TYPE_METADATA = "metadata"
_TYPE_RESULT = "result"
_write_lock = threading.Lock()


def _scan_path(scan_id: str) -> Path | None:
    """Return a safe path for a generated UUID, or None for an invalid ID."""
    try:
        canonical_id = str(uuid.UUID(scan_id))
    except (ValueError, TypeError, AttributeError):
        return None
    return SCAN_DIR / f"{canonical_id}.jsonl"


def save_scan_sync(scan_id: str, data: dict) -> None:
    """Write one complete scan snapshot atomically and safely across threads."""
    path = _scan_path(scan_id)
    if path is None:
        raise ValueError("scan_id must be a UUID")
    tmp = path.with_suffix(".tmp")
    lines = [json.dumps({
        "_type": _TYPE_METADATA,
        "scan_id": data.get("scan_id", scan_id),
        "target": data.get("target"),
        "status": data.get("status"),
        "timestamp": data.get("timestamp"),
        "error": data.get("error"),
    })]
    lines.extend(json.dumps({"_type": _TYPE_RESULT, **finding}) for finding in data.get("results", []))
    content = "\n".join(lines) + "\n"
    try:
        with _write_lock:
            tmp.write_text(content, encoding="utf-8")
            tmp.replace(path)
    except OSError as exc:
        raise IOError(f"Failed to save scan {scan_id}: {exc}") from exc


async def save_scan(scan_id: str, data: dict) -> None:
    """Async wrapper for the synchronous atomic writer."""
    await asyncio.to_thread(save_scan_sync, scan_id, data)


async def load_scan(scan_id: str) -> dict | None:
    """Load a scan snapshot; malformed IDs and missing scans return None."""
    path = _scan_path(scan_id)
    if path is None or not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise IOError(f"Failed to read scan {scan_id}: {exc}") from exc

    metadata = None
    results = []
    try:
        for raw_line in content.splitlines():
            if not raw_line.strip():
                continue
            item = json.loads(raw_line)
            if item.get("_type") == _TYPE_METADATA:
                metadata = item
            elif item.get("_type") == _TYPE_RESULT:
                results.append({key: value for key, value in item.items() if key != "_type"})
    except json.JSONDecodeError as exc:
        raise IOError(f"Failed to parse scan {scan_id}: {exc}") from exc

    if metadata is None:
        return None
    return {
        "scan_id": metadata.get("scan_id"),
        "target": metadata.get("target"),
        "status": metadata.get("status"),
        "timestamp": metadata.get("timestamp"),
        "error": metadata.get("error"),
        "results": results,
    }


async def get_scans_by_target(target: str, limit: int = 10) -> list[dict]:
    """Return the most recent scan records for a target URL."""
    if limit < 1:
        return []
    scans = []
    for path in SCAN_DIR.glob("*.jsonl"):
        scan = await load_scan(path.stem)
        if scan and scan.get("target") == target:
            scans.append(scan)
    scans.sort(key=lambda scan: scan.get("timestamp") or "", reverse=True)
    return scans[:limit]
