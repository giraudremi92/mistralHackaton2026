# Memory

This file is loaded as persistent context for the agent.
Add any persistent knowledge, facts, or preferences here.

## Culture Data

Cultural venue and event files are stored in the culture_data/ folder at the project root.

### Taxonomy (mots-clés / catégories)
culture_data/categories.json — Liste des catégories : Cinéma, Théâtre, Concerts et Salons (Forum Grimaldi), Médiathèque, Musée, Opéra Garnier, Grand Prix Monaco, Rolex Monte-Carlo Masters, Foot, Basket, Jardin exotique, Événements majeurs. Chaque catégorie a un id, un label et des tags_align pour lier les events JSON.

### Sources (pour le scraper)
culture_data/sources.json — Sites et flux à scraper : culture.mc, Grimaldi Forum, flux RSS, flux Grand Prix, TV Monaco / Monaco Info, journal. Chaque source est reliée à des catégories.

### Venues (static info — Markdown)
culture_data/MUSEE_OCEANO.md — Musée Océanographique de Monaco (hours, prices, collections, access)
culture_data/GRIMALDI_FORUM.md — Grimaldi Forum Monaco (venue info, access, general info)

### Events (dynamic data — JSON)
culture_data/events_musee_oceano.json — Events at the Musée Océanographique
culture_data/events_grimaldi_forum.json — Events at the Grimaldi Forum

### JSON event schema
Each event object contains: id, lieu_id, lieu_nom, titre, description, date_start, date_end, heure_debut, heure_fin, tags, tarif, tarif_value, gratuit, url, image_url, source, scraped_at. Les tags doivent s’aligner avec les catégories (categories.json) pour le filtrage et la recherche.