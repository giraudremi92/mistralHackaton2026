"""
Scraper / scheduler — lance manuellement ou via cron.

Usage:
    python scraper/run.py                         # scrape tous les lieux
    python scraper/run.py --venue musee_oceano    # scrape un seul lieu
    python scraper/run.py --dry-run               # affiche sans sauvegarder
    python scraper/run.py --debug --venue grimaldi_forum  # affiche le contenu brut Tavily
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scraper.sources import VENUES
from scraper import fetch, extract, store


def process_venue(venue: dict, dry_run: bool = False, debug: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"Venue : {venue['lieu_nom']}")
    print(f"{'='*60}")

    # 1. Fetch raw content
    print("\n[1/3] Fetching content...")
    t0 = time.time()
    raw_content = fetch.get_raw_content(venue)
    print(f"  Done in {time.time() - t0:.1f}s")
    if not raw_content.strip():
        print("  No content retrieved. Skipping.")
        return

    if debug:
        print(f"\n--- RAW CONTENT ({len(raw_content)} chars) ---")
        print(raw_content[:3000])
        print("--- END RAW CONTENT (truncated) ---\n")

    # 2. Extract structured events via Mistral
    print("\n[2/3] Extracting events with Mistral...")
    t0 = time.time()
    new_events = extract.extract_events(raw_content, venue)
    print(f"  Done in {time.time() - t0:.1f}s")
    if not new_events:
        print("  No events extracted.")
    else:
        print(f"  {len(new_events)} event(s) extracted.")

    # 3. Generate MD if missing
    md_path = Path(venue["md_file"])
    if not md_path.exists():
        print(f"\n[MD] {md_path} not found — generating...")
        venue_info = fetch.get_venue_info(venue)
        if venue_info:
            md_content = extract.generate_venue_md(venue_info, venue)
        else:
            md_content = None

        if dry_run:
            print("  [dry-run] Would create MD file.")
        else:
            created = store.ensure_md(venue, md_content)
            if created:
                print(f"  Created {md_path}")
            else:
                print(f"  {md_path} already exists, skipping.")
    else:
        print(f"\n[MD] {md_path} already exists — skipping.")

    # 4. Upsert / replace events
    mode = "REPLACE (always_current)" if venue.get("always_current") else "UPSERT"
    print(f"\n[3/3] Saving events to {venue['events_file']} [{mode}]...")
    if dry_run:
        existing = store.load_existing(venue["events_file"])
        if venue.get("always_current"):
            print(f"  [dry-run] Would replace {len(existing)} existing event(s) with {len(new_events)} new one(s).")
        else:
            _, added, skipped = store.merge_events(existing, new_events)
            print(f"  [dry-run] Would add {added} event(s), skip {skipped} duplicate(s).")
    else:
        stats = store.upsert_events(venue, new_events)
        print(f"  Existing : {stats['existing']}")
        print(f"  Extracted: {stats['extracted']}")
        print(f"  Added    : {stats['added']}")
        print(f"  Skipped  : {stats['skipped']} (already present)")
        print(f"  Total    : {stats['total']}")


def main():
    parser = argparse.ArgumentParser(description="Scrape cultural events for Monaco venues.")
    parser.add_argument("--venue", help="lieu_id to process (default: all)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Extract only, do not save")
    parser.add_argument("--debug", action="store_true", help="Print raw Tavily content before extraction")
    args = parser.parse_args()

    venues = VENUES
    if args.venue:
        venues = [v for v in VENUES if v["lieu_id"] == args.venue]
        if not venues:
            print(f"Unknown venue: {args.venue}")
            print(f"Available: {[v['lieu_id'] for v in VENUES]}")
            sys.exit(1)

    print(f"Monaco Cultural Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'} {'| DEBUG' if args.debug else ''}")
    print(f"Venues: {[v['lieu_id'] for v in venues]}")

    for venue in venues:
        try:
            process_venue(venue, dry_run=args.dry_run, debug=args.debug)
        except Exception as e:
            print(f"\n  ERROR processing {venue['lieu_id']}: {e}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
