# Memory

This file is loaded as persistent context for the agent.
Add any persistent knowledge, facts, or preferences here.

## Culture Data

Cultural venue and event files are stored in the `culture_data/` folder at the project root.

### Venues (static info — Markdown)
- `culture_data/MUSEE_OCEANO.md` — Musée Océanographique de Monaco (hours, prices, collections, access)
- `culture_data/GRIMALDI_FORUM.md` — Grimaldi Forum Monaco (venue info, access, general info)

### Events (dynamic data — JSON)
- `culture_data/events_musee_oceano.json` — Events at the Musée Océanographique
- `culture_data/events_grimaldi_forum.json` — Events at the Grimaldi Forum

### JSON event schema
Each event object contains: `id`, `venue_id`, `venue_name`, `titre`, `description`, `date_start`, `date_end`, `heure_debut`, `heure_fin`, `tags`, `tarif`, `tarif_value`, `gratuit`, `url`, `image_url`, `source`, `scraped_at`.
