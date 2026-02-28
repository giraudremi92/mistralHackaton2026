import json
from datetime import date, datetime
from pathlib import Path

from dateparser.search import search_dates

from agent.providers import chat

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_FILES = [ROOT / "SYSTEM_PROMPT.md", ROOT / "MEMORY.md"]
CULTURE_DATA_DIR = ROOT / "culture_data"
CATEGORIES_FILE = CULTURE_DATA_DIR / "categories.json"
DATE_LANGUAGES = ["fr", "en", "es", "it", "ru"]
MAX_EVENTS_IN_FIXED_LIST = 50
FALLBACK_MESSAGE = "Désolé, impossible de répondre pour le moment."


def extract_date_range(text: str) -> tuple[date | None, date | None]:
    if not text or not text.strip():
        return (None, None)
    settings = {"RELATIVE_BASE": datetime.now()}
    results = search_dates(text, languages=DATE_LANGUAGES, settings=settings)
    if not results:
        return (None, None)
    dates_found = [r[1].date() for r in results]
    return (min(dates_found), max(dates_found))


def load_venue_markdown(dir_path: Path) -> str:
    parts = []
    for p in sorted(dir_path.glob("*.md")):
        parts.append(p.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts) if parts else ""


def load_events_json(file_path: Path) -> list[dict]:
    if not file_path.exists():
        return []
    raw = file_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def format_events_summary(events: list[dict]) -> str:
    lines = []
    for e in events:
        titre = e.get("titre", "")
        lieu = e.get("lieu_nom", "")
        start = e.get("date_start", "")
        end = e.get("date_end", "")
        heures = f"{e.get('heure_debut', '')}-{e.get('heure_fin', '')}" if e.get("heure_debut") else ""
        tarif = e.get("tarif", "")
        url = e.get("url", "")
        line = f"- {titre} | {lieu} | {start} → {end} {heures} | {tarif}"
        if url:
            line += f" | {url}"
        lines.append(line)
    return "\n".join(lines)


def format_events_fixed(events: list[dict], max_items: int = MAX_EVENTS_IN_FIXED_LIST) -> str:
    lines = []
    for i, e in enumerate(events[:max_items], 1):
        titre = e.get("titre", "")
        start = e.get("date_start", "")
        end = e.get("date_end", "")
        lieu = e.get("lieu_nom", "")
        tarif = e.get("tarif", "") or "Prix non communiqué"
        url = e.get("url", "")
        line = f"{i}. {titre}. Du {start} au {end}. Lieu : {lieu}. Tarif : {tarif}."
        if url:
            line += f" Lien : {url}."
        lines.append(line)
    return "\n\n".join(lines)


def build_fixed_intro(date_min: date | None, date_max: date | None, count: int) -> str:
    if date_min and date_max:
        period = f"du {date_min.strftime('%d/%m/%Y')} au {date_max.strftime('%d/%m/%Y')}"
    elif date_min:
        period = f"à partir du {date_min.strftime('%d/%m/%Y')}"
    elif date_max:
        period = f"jusqu'au {date_max.strftime('%d/%m/%Y')}"
    else:
        period = "disponibles"
    return f"Événements à Monaco {period}. {count} résultat(s)."


def get_last_scraped_at() -> str:
    all_events = get_all_events()
    scraped_dates = [e.get("scraped_at") for e in all_events if e.get("scraped_at")]
    if scraped_dates:
        try:
            dt = datetime.fromisoformat(scraped_dates[0].replace("Z", "+00:00"))
            for s in scraped_dates[1:]:
                d = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if d > dt:
                    dt = d
            return dt.strftime("%Y-%m-%d à %H:%M")
        except (ValueError, TypeError):
            pass
    return datetime.now().strftime("%Y-%m-%d à %H:%M")


def load_categories_labels() -> list[str]:
    if not CATEGORIES_FILE.exists():
        return []
    try:
        data = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
        cats = data.get("categories") or []
        return [c.get("label", "") for c in cats if c.get("label")]
    except (json.JSONDecodeError, OSError):
        return []


def get_all_events() -> list[dict]:
    all_events = []
    for json_path in sorted(CULTURE_DATA_DIR.glob("events_*.json")):
        all_events.extend(load_events_json(json_path))
    return all_events


def filter_events_by_date(events: list[dict], date_min: date | None, date_max: date | None) -> list[dict]:
    if date_min is None and date_max is None:
        return events
    filtered = []
    for e in events:
        try:
            start_s = e.get("date_start")
            end_s = e.get("date_end")
            event_start = datetime.strptime(start_s, "%Y-%m-%d").date() if start_s else None
            event_end = datetime.strptime(end_s, "%Y-%m-%d").date() if end_s else None
        except (ValueError, TypeError):
            filtered.append(e)
            continue
        if event_start is None and event_end is None:
            filtered.append(e)
            continue
        event_start = event_start or event_end
        event_end = event_end or event_start
        if date_max is not None and event_start > date_max:
            continue
        if date_min is not None and event_end < date_min:
            continue
        filtered.append(e)
    return filtered


def load_culture_context(date_min: date | None = None, date_max: date | None = None) -> str:
    if not CULTURE_DATA_DIR.exists():
        return ""
    parts = []
    labels = load_categories_labels()
    if labels:
        parts.append("## Catégories disponibles\n\n" + ", ".join(labels) + ".")
    venues = load_venue_markdown(CULTURE_DATA_DIR)
    if venues:
        parts.append("## Venues\n\n" + venues)
    all_events = get_all_events()
    events = filter_events_by_date(all_events, date_min, date_max)
    if events:
        parts.append("## Events\n\n" + format_events_summary(events))
    elif date_min is not None or date_max is not None:
        parts.append("## Events\n\nAucun événement trouvé pour la période demandée. Indiquer à l'utilisateur qu'aucun événement ne correspond dans les données et ne pas inventer d'événements.")
    return "\n\n".join(parts) if parts else ""


def load_context(user_message: str | None = None) -> str:
    parts = []
    for p in CONTEXT_FILES:
        if p.exists():
            parts.append(f"# {p.name}\n{p.read_text(encoding='utf-8')}")
    base = "\n\n".join(parts)
    date_min, date_max = extract_date_range(user_message or "")
    culture = load_culture_context(date_min=date_min, date_max=date_max)
    if culture:
        base += "\n\n# Culture data\n\n" + culture
    base = base.replace("{last_scraped_at}", get_last_scraped_at())
    return base


def respond(message: str, history: list, provider: str = "mistral", model: str | None = None) -> str:
    date_min, date_max = extract_date_range(message)
    all_events = get_all_events()
    filtered = filter_events_by_date(all_events, date_min, date_max)

    if date_min is not None or date_max is not None:
        if not filtered:
            period = ""
            if date_min and date_max:
                period = f" du {date_min.strftime('%d/%m/%Y')} au {date_max.strftime('%d/%m/%Y')}"
            elif date_min:
                period = f" à partir du {date_min.strftime('%d/%m/%Y')}"
            elif date_max:
                period = f" jusqu'au {date_max.strftime('%d/%m/%Y')}"
            return f"Aucun événement trouvé pour la période{period}. Vérifiez sur le site officiel ou précisez une autre date."
        intro = build_fixed_intro(date_min, date_max, len(filtered))
        list_str = format_events_fixed(filtered)
        extra = len(filtered) - MAX_EVENTS_IN_FIXED_LIST
        if extra > 0:
            list_str += f"\n\n{extra} autre(s) événement(s) disponible(s). Précisez la date ou le type pour affiner."
        return intro + "\n\n" + list_str

    messages = [{"role": "system", "content": load_context(message)}]
    for msg in history:
        if isinstance(msg, dict):
            messages.append({"role": msg["role"], "content": msg["content"]})
        else:
            user_msg, assistant_msg = msg
            messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": message})
    try:
        return chat(messages, provider=provider, model=model or None)
    except Exception:
        try:
            return chat(messages, provider=provider, model=model or None)
        except Exception:
            return FALLBACK_MESSAGE
