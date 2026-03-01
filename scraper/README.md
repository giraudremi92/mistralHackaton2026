# Monaco Cultural Scraper

Automated pipeline to scrape, extract and store cultural events from Monaco venues.
Built with **Tavily** (web search) + **Linkup** (JS rendering) + **Mistral Large** (LLM extraction).

---

## Architecture

```
sources.json  →  fetch.py  →  extract.py  →  store.py
 (venue config)   (Tavily/Linkup)  (Mistral LLM)   (JSON upsert)
```

**3-stage pipeline per venue:**
1. **Fetch** — search the web + fetch URLs (with optional JS rendering)
2. **Extract** — send raw content to Mistral, get structured JSON events
3. **Store** — upsert events into `culture_data/events_<venue_id>.json`

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys in .env
MISTRAL_API_KEY=...
TAVILY_API_KEY=...
LINKUP_API_KEY=...   # optional but recommended for JS-heavy sites

# Run all venues
python3 scraper/run.py

# Run a single venue
python3 scraper/run.py --venue musee_oceano

# Dry run (extract but don't save)
python3 scraper/run.py --dry-run

# Debug mode (prints raw fetched content)
python3 scraper/run.py --debug --venue grimaldi_forum
```

---

## Cron Job (Daily Update)

Add to crontab to run every day at 3:00 AM:

```bash
crontab -e
```

```cron
0 3 * * * cd /path/to/mistralHackaton2026 && python3 scraper/run.py >> /var/log/monaco_scraper.log 2>&1
```

Or with dotenv:

```cron
0 3 * * * cd /path/to/mistralHackaton2026 && /usr/bin/python3 scraper/run.py >> logs/scraper.log 2>&1
```

**Recommended frequency:** Daily — events are published on a rolling basis, and the upsert logic ensures no duplicates across runs.

---

## Configuration: `sources.json`

Each venue is a JSON object. All fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `venue_id` | string | ✅ | Unique identifier (slug) |
| `venue_name` | string | ✅ | Display name |
| `search_queries` | string[] | ✅ | Tavily search queries (can be `[]` for Linkup-only venues) |
| `urls` | string[] | ✅ | Direct URLs to fetch (can be `[]`) |
| `events_file` | string | ✅ | Output JSON path |
| `md_file` | string | ✅ | Venue info markdown path |
| `md_search_query` | string | ✅ | Query for venue static info |
| `always_current` | bool | — | If true: REPLACE all events on each run (e.g. cinema) |
| `season` | string | — | Theatrical season e.g. `"2025-2026"`. Sept–Dec → year1, Jan–Jun → year2 |
| `render_js` | bool | — | Enable JS rendering for URL fetch (default: `true`) |
| `fetch_provider` | string | — | `"auto"` \| `"linkup"` \| `"tavily"` (default: `"auto"`) |
| `md_context` | string | — | Extra context injected into MD generation prompt |

### Template variables in `search_queries` and `urls`

| Variable | Value |
|----------|-------|
| `{year}` | Current target year (min 2026) |
| `{today}` | Today's date `YYYY-MM-DD` |
| `{season}` | Full season e.g. `2025-2026` |
| `{season_year1}` | First year of season e.g. `2025` |
| `{season_year2}` | Second year of season e.g. `2026` |

**Example:**
```json
"search_queries": [
  "Théâtre Princesse Grace Monaco mars avril {season_year2} spectacles"
]
```

---

## Fetch Providers

| Provider | JS Rendering | Notes |
|----------|-------------|-------|
| `tavily` | No | Fast, good for static sites and search queries |
| `linkup` | Yes | Preferred for JS-heavy or dynamic sites. Fetches URLs directly — no search queries needed. |
| `auto` | Yes if Linkup available | Falls back to Tavily if `LINKUP_API_KEY` not set |

Set per venue with `"fetch_provider": "linkup"` in `sources.json`.

---

## Store Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **REPLACE** | `always_current: true` | All events replaced on each run (e.g. cinema: weekly programme) |
| **UPSERT** | default | New events added, existing preserved. Key: `(venue_id, title_normalized, date_start)` |
| **PRUNE** | `season` field present | Past events automatically removed after each upsert |

**Deduplication** normalizes titles: lowercase, accent removal, punctuation stripping.
`"Noëlle Perna"` and `"NOELLE PERNA"` are treated as the same event.

---

## Venue MD Files

Static venue info files (`culture_data/*.md`) are generated **once** on first run if missing.
They contain: address, opening hours, prices, accessibility, tags.

To regenerate a venue's MD file, delete it and re-run the scraper:
```bash
rm culture_data/MUSEE_OCEANO.md
python3 scraper/run.py --venue musee_oceano
```

---

## Current Venues

| ID | Venue | Method | Notes |
|----|-------|--------|-------|
| `musee_oceano` | Musée Océanographique | Tavily search + URL | Standard UPSERT |
| `grimaldi_forum` | Grimaldi Forum | Tavily search only | Site blocks direct fetch |
| `cinema_monaco` | Cinémas de Monaco | Linkup only | REPLACE weekly; showtimes vary by day |
| `mediatheque_monaco` | Médiathèque de Monaco | Linkup only | SPA calendar |
| `theatre_muses` | Théâtre des Muses | Linkup only | Season 2025-2026 |
| `theatre_princesse_grace` | Théâtre Princesse Grace | Linkup only | Season 2025-2026 |

---

## Adding a New Venue

1. Add an entry to `scraper/sources.json`
2. Run `python3 scraper/run.py --venue <new_id> --debug` to test
3. Check `culture_data/events_<new_id>.json` for extracted events

**Tips:**
- Use `--debug` to inspect raw fetched content before extraction
- If the site uses JavaScript: set `"fetch_provider": "linkup"`
- If the site is a seasonal theatre: add `"season": "YYYY-YYYY"`
- If the site blocks all bots: use Tavily search queries only (`"urls": []`)
