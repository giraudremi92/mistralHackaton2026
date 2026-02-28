"""Upsert events into JSON files — never overwrites existing events."""

import json
import re
from datetime import datetime
from pathlib import Path


def _event_key(event: dict) -> tuple:
    """Unique key for an event: (lieu_id, titre_normalized, date_start)."""
    titre = re.sub(r"\s+", " ", event.get("titre", "")).strip().lower()
    return (event.get("lieu_id", ""), titre, event.get("date_start", ""))


def load_existing(filepath: str) -> list[dict]:
    p = Path(filepath)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        return []


def merge_events(existing: list[dict], new_events: list[dict]) -> tuple[list[dict], int, int]:
    """
    Merge new_events into existing.
    Returns (merged_list, added_count, skipped_count).
    """
    index = {_event_key(e): e for e in existing}
    added = 0
    skipped = 0

    for event in new_events:
        key = _event_key(event)
        if key not in index:
            index[key] = event
            added += 1
        else:
            skipped += 1

    # Sort by date_start
    merged = sorted(index.values(), key=lambda e: e.get("date_start", ""))
    return merged, added, skipped


def save_events(filepath: str, events: list[dict]) -> None:
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def save_md(filepath: str, content: str) -> None:
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def upsert_events(venue: dict, new_events: list[dict]) -> dict:
    """
    For always_current venues: replace all events (programmation toujours à jour).
    For others: merge/upsert (ne jamais écraser les events existants).
    Returns stats dict.
    """
    filepath = venue["events_file"]
    existing = load_existing(filepath)

    if venue.get("always_current"):
        save_events(filepath, new_events)
        return {
            "file": filepath,
            "existing": len(existing),
            "extracted": len(new_events),
            "added": len(new_events),
            "skipped": 0,
            "total": len(new_events),
            "mode": "replace",
        }

    merged, added, skipped = merge_events(existing, new_events)
    save_events(filepath, merged)
    return {
        "file": filepath,
        "existing": len(existing),
        "extracted": len(new_events),
        "added": added,
        "skipped": skipped,
        "total": len(merged),
        "mode": "upsert",
    }


def ensure_md(venue: dict, generated_content: str | None) -> bool:
    """
    Create MD file if it doesn't exist.
    Returns True if file was created, False if it already existed.
    """
    p = Path(venue["md_file"])
    if p.exists():
        return False
    if generated_content:
        save_md(venue["md_file"], generated_content)
        return True
    return False
