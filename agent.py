import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from providers import chat

CONTEXT_FILES = ["SYSTEM_PROMPT.md", "MEMORY.md"]
CULTURE_DATA_DIR = Path("culture_data")


def effective_today() -> date:
    """Return today's date, adjusted to 2026 if system clock is behind the data."""
    today = date.today()
    if today.year < 2026:
        return today.replace(year=2026)
    return today


def load_static_context() -> str:
    """Load system prompt, memory and venue MD files."""
    today = effective_today()
    parts = [f"# Date du jour\nNous sommes le {today.strftime('%A %d %B %Y')} (date de référence pour toutes les questions temporelles)."]

    for fname in CONTEXT_FILES:
        p = Path(fname)
        if p.exists():
            parts.append(f"# {fname}\n{p.read_text()}")

    if CULTURE_DATA_DIR.is_dir():
        for f in sorted(CULTURE_DATA_DIR.iterdir()):
            if f.suffix == ".md":
                parts.append(f"## {f.name}\n{f.read_text()}")

    return "\n\n".join(parts)


def _next_occurrence(day: int, month: int, today: date) -> date:
    """Return the closest future date for a given day/month."""
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
            if candidate >= today:
                return candidate
        except ValueError:
            pass
    return date(today.year, month, day)


def extract_date_range(message: str) -> tuple[date, date] | None:
    """
    Extract a date range from the user message.
    Returns (date_from, date_to) or None if no date detected.
    """
    today = effective_today()

    if re.search(r"\baujourd'hui\b", message, re.IGNORECASE):
        return (today, today)

    if re.search(r"\bdemain\b", message, re.IGNORECASE):
        tomorrow = today + timedelta(days=1)
        return (tomorrow, tomorrow)

    if re.search(r"\bce week[-\s]?end\b", message, re.IGNORECASE):
        # Next Saturday and Sunday from today
        days_until_saturday = (5 - today.weekday()) % 7
        saturday = today + timedelta(days=days_until_saturday)
        sunday = saturday + timedelta(days=1)
        return (saturday, sunday)

    # French month names
    months = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4,
        "mai": 5, "juin": 6, "juillet": 7, "août": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    }
    pattern = r"\b(\d{1,2})\s+(" + "|".join(months.keys()) + r")(?:\s+(\d{4}))?\b"
    match = re.search(pattern, message, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month = months[match.group(2).lower()]
        if match.group(3):
            d = date(int(match.group(3)), month, day)
        else:
            d = _next_occurrence(day, month, today)
        return (d, d)

    # ISO format YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", message)
    if match:
        try:
            d = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return (d, d)
        except ValueError:
            pass

    return None


def load_events(date_range: tuple[date, date] | None) -> str:
    """Load and filter JSON events by date range. None = no filter."""
    if not CULTURE_DATA_DIR.is_dir():
        return ""

    all_events = []
    for f in sorted(CULTURE_DATA_DIR.iterdir()):
        if f.suffix == ".json":
            try:
                all_events.extend(json.loads(f.read_text()))
            except (json.JSONDecodeError, Exception):
                pass

    def _matches(event, from_date, to_date) -> bool:
        start = datetime.strptime(event["date_start"], "%Y-%m-%d").date()
        if event.get("always_current"):
            # Scraped content: available from scrape date onwards, no end date
            return start <= to_date
        end_raw = event.get("date_end")
        if not end_raw:
            return start <= to_date
        end = datetime.strptime(end_raw, "%Y-%m-%d").date()
        return start <= to_date and end >= from_date

    def _filter(events, from_date, to_date):
        return [e for e in events if _matches(e, from_date, to_date)]

    if date_range is not None:
        from_date, to_date = date_range
        filtered = _filter(all_events, from_date, to_date)

        # If no results, try +1 year (handles mismatch between system date and data year)
        if not filtered:
            from_date_next = from_date.replace(year=from_date.year + 1)
            to_date_next = to_date.replace(year=to_date.year + 1)
            filtered = _filter(all_events, from_date_next, to_date_next)
    else:
        filtered = all_events

    if not filtered:
        return "## Événements disponibles\nAucun événement trouvé pour cette période.\n"

    lines = ["## Événements disponibles\n"]
    for e in filtered:
        lines.append(f"### {e['titre']} ({e['lieu_nom']})")
        if e.get("always_current"):
            lines.append(f"- Disponibilité : À l'affiche en ce moment")
        else:
            lines.append(f"- Date : {e['date_start']} → {e['date_end']}")
            if e.get("heure_debut"):
                lines.append(f"- Horaires : {e['heure_debut']} – {e.get('heure_fin', '')}")
        if e.get("tarif"):
            lines.append(f"- Tarif : {e['tarif']}")
        if e.get("url"):
            lines.append(f"- Lien : {e['url']}")
        if e.get("description"):
            lines.append(f"- {e['description']}")
        lines.append("")

    return "\n".join(lines)


def respond(message: str, history: list, provider: str = "mistral", model: str | None = None) -> str:
    """Build messages from history + context, call LLM, return response."""
    date_range = extract_date_range(message)
    system_content = load_static_context() + "\n\n" + load_events(date_range)

    messages = [{"role": "system", "content": system_content}]

    for msg in history:
        if isinstance(msg, dict):
            messages.append({"role": msg["role"], "content": msg["content"]})
        else:
            user_msg, assistant_msg = msg
            messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})

    messages.append({"role": "user", "content": message})
    return chat(messages, provider=provider, model=model or None)
