"""Use Mistral to extract structured events and venue info from raw content."""

import json
import os
import re
from datetime import datetime, timedelta

from mistralai import Mistral

MODEL = "mistral-large-latest"  # better instruction following for complex extraction


def get_client() -> Mistral:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY not set in environment.")
    return Mistral(api_key=api_key)


def fix_season_years(events: list[dict], season: str) -> list[dict]:
    """Fix event years for a theatrical season (e.g. '2025-2026').

    Convention: months Sept-Dec → first year, months Jan-Aug → second year.
    Applied to both date_start and date_end.
    """
    parts = season.split("-")
    if len(parts) != 2:
        return events
    year1, year2 = int(parts[0]), int(parts[1])

    for event in events:
        for field in ("date_start", "date_end"):
            val = event.get(field)
            if not val:
                continue
            try:
                dt = datetime.strptime(val, "%Y-%m-%d")
                correct_year = year1 if dt.month >= 9 else year2
                if dt.year != correct_year:
                    event[field] = dt.replace(year=correct_year).strftime("%Y-%m-%d")
            except ValueError:
                pass
        # Recompute id to reflect corrected date_start
        if event.get("date_start") and event.get("lieu_id") and event.get("titre"):
            slug = re.sub(r"[^a-z0-9]+", "-", event["titre"].lower()).strip("-")
            event["id"] = f"{event['lieu_id']}_{slug}_{event['date_start']}"

    return events


def extract_events(raw_content: str, venue: dict) -> list[dict]:
    """Ask Mistral to extract events from raw scraped content."""
    client = get_client()
    current_year = datetime.now().year
    target_year = current_year if current_year >= 2026 else 2026

    scraped_at = datetime.utcnow()
    always_current = venue.get("always_current", False)
    duration_days = venue.get("current_duration_days", 45)
    default_start = scraped_at.strftime("%Y-%m-%d")

    season = venue.get("season")  # e.g. "2025-2026"

    if always_current:
        date_rule = f"""Pour les dates : ce lieu affiche sa programmation en cours au moment du scraping.
- date_start = date du scraping = {default_start} (pour tous les événements sans exception)
- date_end = null (pas de date de fin, la disponibilité est gérée par le système)
- Ajoute le champ "always_current": true dans chaque événement
- Ne pas chercher à deviner des dates futures précises
- Pour heure_debut : si plusieurs séances existent, indique la première séance de la journée (format HH:MM)
- Pour la description : inclus les horaires de toutes les séances et la salle (ex: "Salle 1 : 14h00, 16h15 | Salle 2 : 20h50")"""
        year_filter = f"de {target_year}"
    elif season:
        s_parts = season.split("-")
        sy1, sy2 = s_parts[0], s_parts[1]
        date_rule = f"""Pour les dates : ce lieu suit une saison théâtrale {season}.
Règle d'attribution des années (OBLIGATOIRE) :
- Mois septembre (09) à décembre (12) → année {sy1}
- Mois janvier (01) à août (08) → année {sy2}
Si le contenu mentionne un mois sans année, applique cette règle.
Si plusieurs dates pour un même événement, crée une entrée par date."""
        year_filter = f"de la saison {season} ({sy1} et {sy2})"
    else:
        date_rule = f"""Pour les dates :
- Si un événement se déroule sur plusieurs jours (ex: "ven. 11 - dim. 13 décembre"), crée UNE SEULE entrée avec date_start = premier jour et date_end = dernier jour. Ne crée PAS une entrée par jour.
- Si plusieurs événements distincts ont des dates différentes, crée une entrée par événement.
- Si le contenu mentionne un mois sans date précise (ex: "en mars"), utilise le 1er du mois comme date_start et le dernier jour du mois comme date_end."""
        year_filter = f"de {target_year}"

    prompt = f"""Tu es un extracteur de données structurées spécialisé en événements culturels.

À partir du contenu brut ci-dessous, extrais uniquement les ÉVÉNEMENTS CULTURELS {year_filter} pour le lieu "{venue['lieu_nom']}".

Un événement culturel valide est : concert, exposition, spectacle, festival, atelier, visite guidée, conférence, projection de film, comédie musicale, opéra, pièce de théâtre, séance de cinéma.

NE PAS extraire : offres promotionnelles, réductions, podcasts, articles de blog, offres d'emploi, recrutements, communiqués de presse, newsletters, actualités générales.

{date_rule}

Retourne UNIQUEMENT un tableau JSON valide (pas de texte avant ou après) :
{{
  "id": "{venue['lieu_id']}_<slug-titre>_<date_start>",
  "lieu_id": "{venue['lieu_id']}",
  "lieu_nom": "{venue['lieu_nom']}",
  "titre": "string",
  "description": "string",
  "date_start": "YYYY-MM-DD",
  "date_end": "YYYY-MM-DD ou null",
  "always_current": false,
  "heure_debut": "HH:MM ou null",
  "heure_fin": "HH:MM ou null",
  "tags": ["string"],
  "tarif": "string ou null",
  "tarif_value": 0,
  "gratuit": false,
  "url": "string ou null",
  "image_url": "string ou null",
  "source": "{venue['urls'][0] if venue.get('urls') else ''}",
  "scraped_at": "{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}"
}}

Règles :
- Utilise le titre en FRANÇAIS si disponible. Ne traduis jamais un titre depuis une autre langue.
- tarif_value = prix entier minimum en euros (0 si gratuit)
- gratuit = true si tarif_value == 0
- id = lieu_id + "_" + slug titre en minuscules avec tirets + "_" + date_start
- Si aucun événement valide trouvé, retourne []

Contenu brut :
{raw_content[:100000]}
"""

    try:
        response = client.chat.complete(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
    except Exception as e:
        print(f"  Warning: Mistral call failed or timed out: {e}")
        return []

    raw = response.choices[0].message.content.strip()

    # Extract JSON array from response (model sometimes wraps in ```json)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        print(f"  Warning: no JSON array found in Mistral response")
        return []

    try:
        events = json.loads(match.group())
        # Post-process: fix years for seasonal venues (belt + suspenders)
        if season:
            events = fix_season_years(events, season)
        print(f"  Extracted {len(events)} event(s)")
        return events
    except json.JSONDecodeError as e:
        print(f"  Warning: JSON parse error: {e}")
        return []


def generate_venue_md(raw_content: str, venue: dict) -> str:
    """Ask Mistral to generate a venue MD file from raw content."""
    client = get_client()

    md_context = venue.get("md_context", "")
    context_block = f"\nInformations importantes à respecter impérativement :\n{md_context}\n" if md_context else ""

    prompt = f"""Tu es un rédacteur de fiches pratiques.

À partir du contenu brut ci-dessous, génère une fiche Markdown pour le lieu "{venue['lieu_nom']}".
{context_block}
La fiche doit contenir :
- Titre (# Nom du lieu)
- Présentation (2-3 phrases)
- Tableau informations pratiques (adresse, horaires, tarifs, site web, téléphone, accès)
- Collections/offres permanentes (liste à puces)
- Accessibilité
- Tags (liste de mots-clés)

Retourne UNIQUEMENT le contenu Markdown brut, sans bloc de code, sans backticks, sans texte introductif.
Le titre H1 doit être EXACTEMENT : # {venue['lieu_nom']}

Format attendu (commence directement par la ligne #) :
# {venue['lieu_nom']}

<!-- TYPE: lieu_statique -->
<!-- CATEGORY: [categorie] -->
<!-- LAST_UPDATED: {datetime.utcnow().strftime('%Y-%m-%d')} -->

## Présentation
...

## Informations pratiques
| Info | Détail |
|------|--------|
...

## Collections permanentes / Programmation
...

## Accessibilité
...

## Tags agent
`tag1` `tag2` ...

Contenu brut :
{raw_content[:8000]}
"""

    response = client.chat.complete(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = response.choices[0].message.content.strip()
    # Strip any accidental ```markdown ... ``` wrapping
    content = re.sub(r"^```[a-z]*\n?", "", content).rstrip("`").strip()
    return content
