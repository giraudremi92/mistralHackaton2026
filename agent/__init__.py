import json
from datetime import date, datetime, timedelta
from pathlib import Path

from dateparser.search import search_dates
from langdetect import detect, LangDetectException

from agent.providers import chat

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "it": "Italian",
    "ru": "Russian",
    "es": "Spanish",
    "nl": "Dutch",
}

FRENCH_ACCENTS = "éèêëàâäùûüîïôöç"
FRENCH_WORD_MARKERS = ("ce ", "cette ", " les ", " des ", " pour ", " dans ", " avec ", " une ", " que ", " est ", " sont ", " week-end", " semaine", " films ", " film ", " concert", " expos")
CONFUSABLE_WITH_FRENCH = ("de", "nl")

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_FILES = [ROOT / "SYSTEM_PROMPT.md", ROOT / "MEMORY.md"]
CULTURE_DATA_DIR = ROOT / "culture_data"
CATEGORIES_FILE = CULTURE_DATA_DIR / "categories.json"
DATE_LANGUAGES = ["fr", "en", "es", "it", "ru"]
FALLBACK_MESSAGE = "Désolé, impossible de répondre pour le moment."

WEEKEND_PATTERNS = (
    "ce weekend", "ce week-end", "ce week end", "this weekend",
)
WEEK_PATTERNS = (
    "cette semaine", "this week",
)

def _current_week_bounds(ref: date) -> tuple[date, date]:
    weekday = ref.weekday()
    week_start = ref - timedelta(days=weekday)
    week_end = week_start + timedelta(days=6)
    return (week_start, week_end)


def _current_weekend_bounds(ref: date) -> tuple[date, date]:
    week_start, week_end = _current_week_bounds(ref)
    saturday = week_start + timedelta(days=5)
    sunday = week_end
    return (saturday, sunday)


def _parse_relative_period(text: str, ref: date) -> tuple[date | None, date | None]:
    lower = text.lower().strip()
    for p in WEEKEND_PATTERNS:
        if p in lower:
            return _current_weekend_bounds(ref)
    for p in WEEK_PATTERNS:
        if p in lower:
            return _current_week_bounds(ref)
    return (None, None)


def extract_date_range(text: str) -> tuple[date | None, date | None]:
    if not text or not text.strip():
        return (None, None)
    ref = datetime.now().date()
    settings = {"RELATIVE_BASE": datetime.now()}
    results = search_dates(text, languages=DATE_LANGUAGES, settings=settings)
    if results:
        dates_found = [r[1].date() for r in results]
        return (min(dates_found), max(dates_found))
    return _parse_relative_period(text, ref)


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
        titre = e.get("title", "")
        lieu = e.get("venue_name", "")
        start = e.get("date_start", "")
        end = e.get("date_end", "")
        heures = f"{e.get('start_time', '')}-{e.get('end_time', '')}" if e.get("start_time") else ""
        tarif = e.get("price", "")
        url = e.get("url", "")
        line = f"- {titre} | {lieu} | {start} → {end} {heures} | {tarif}"
        if url:
            line += f" | {url}"
        lines.append(line)
    return "\n".join(lines)


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
        if e.get("always_current") and event_start is not None:
            if date_max is not None and event_start > date_max:
                continue
            filtered.append(e)
            continue
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


def _has_french_markers(text: str) -> bool:
    lower = text.lower()
    if any(c in lower for c in FRENCH_ACCENTS):
        return True
    return any(m in lower for m in FRENCH_WORD_MARKERS)


def _detect_reply_language(user_message: str | None) -> str | None:
    if not (user_message or user_message.strip()):
        return None
    text = user_message.strip()[:500]
    if len(text) < 10:
        return None
    try:
        code = detect(text)
        if code == "de":
            code = "fr"
        if code in CONFUSABLE_WITH_FRENCH and _has_french_markers(text):
            code = "fr"
        return LANGUAGE_NAMES.get(code, code)
    except LangDetectException:
        return None


def load_context(user_message: str | None = None) -> str:
    lang_name = _detect_reply_language(user_message)
    parts = []
    if lang_name:
        parts.append(
            f"# CRITICAL – Language\n\n"
            f"The user wrote in {lang_name}. You MUST reply entirely in {lang_name}. "
            f"Do not use French or any other language. Every sentence of your answer must be in {lang_name}."
        )
    for p in CONTEXT_FILES:
        if p.exists():
            parts.append(f"# {p.name}\n{p.read_text(encoding='utf-8')}")
    base = "\n\n".join(parts)
    date_min, date_max = extract_date_range(user_message or "")
    culture = load_culture_context(date_min=date_min, date_max=date_max)
    if culture:
        base += "\n\n# Culture data\n\n" + culture
    if lang_name:
        base += f"\n\n# Reminder: reply only in {lang_name}. Do not use French unless the user wrote in French."
    base = base.replace("{last_scraped_at}", get_last_scraped_at())
    return base


def respond(message: str, history: list, provider: str = "mistral", model: str | None = None) -> str | dict:
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
