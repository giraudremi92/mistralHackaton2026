"""Fetch raw content using Tavily search + Linkup (with JS rendering support)."""

import os
from datetime import date
from typing import Any

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from linkup import LinkupClient
    LINKUP_AVAILABLE = True
except ImportError:
    LINKUP_AVAILABLE = False


def get_tavily() -> Any:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY not set in environment.")
    if not TAVILY_AVAILABLE:
        raise ImportError("tavily-python not installed. Run: pip install tavily-python")
    return TavilyClient(api_key=api_key)


def get_linkup() -> Any:
    api_key = os.getenv("LINKUP_API_KEY")
    if not api_key:
        raise EnvironmentError("LINKUP_API_KEY not set in environment.")
    if not LINKUP_AVAILABLE:
        raise ImportError("linkup-sdk not installed. Run: pip install linkup-sdk")
    return LinkupClient(api_key=api_key)


def search_events(query: str, max_results: int = 5) -> str:
    """Search web for events and return concatenated content."""
    client = get_tavily()
    results = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_raw_content=True,
    )
    parts = []
    for r in results.get("results", []):
        content = r.get("raw_content") or r.get("content", "")
        if content:
            parts.append(f"[Source: {r.get('url', '')}]\n{content}")
    return "\n\n---\n\n".join(parts)


def fetch_urls_tavily(urls: list[str]) -> str:
    """Fetch specific URLs via Tavily extract."""
    client = get_tavily()
    parts = []
    for url in urls:
        try:
            result = client.extract(urls=[url])
            for r in result.get("results", []):
                content = r.get("raw_content") or r.get("content", "")
                if content:
                    parts.append(f"[Source: {url}]\n{content}")
        except Exception as e:
            print(f"  Warning: Tavily could not fetch {url}: {e}")
    return "\n\n---\n\n".join(parts)


def fetch_urls_linkup(urls: list[str], render_js: bool = False) -> str:
    """Fetch specific URLs via Linkup (supports JS rendering)."""
    client = get_linkup()
    parts = []
    for url in urls:
        try:
            result = client.fetch(url=url, render_js=render_js)
            content = result.content if hasattr(result, "content") else str(result)
            if content:
                parts.append(f"[Source: {url}]\n{content}")
        except Exception as e:
            print(f"  Warning: Linkup could not fetch {url}: {e}")
    return "\n\n---\n\n".join(parts)


def fetch_urls(urls: list[str], render_js: bool = False, provider: str = "auto") -> str:
    """Fetch URLs with configurable provider.

    provider:
      "auto"   — Linkup with render_js if available, else Tavily (default)
      "linkup" — force Linkup (render_js=True)
      "tavily" — force Tavily
    """
    use_linkup = LINKUP_AVAILABLE and os.getenv("LINKUP_API_KEY")

    if provider == "tavily":
        return fetch_urls_tavily(urls)
    elif provider == "linkup":
        print(f"  Using Linkup (render_js=True)...")
        return fetch_urls_linkup(urls, render_js=True)
    else:  # auto
        if render_js and use_linkup:
            print(f"  Using Linkup (render_js=True)...")
            return fetch_urls_linkup(urls, render_js=True)
        return fetch_urls_tavily(urls)


def get_raw_content(venue: dict) -> str:
    """Get raw content for a venue using search + direct URL fetch."""
    parts = []

    today = date.today()
    current_year = today.year
    target_year = current_year if current_year >= 2026 else 2026

    # Compute season years if applicable (e.g. "2025-2026" → year1=2025, year2=2026)
    season = venue.get("season", "")
    season_parts = season.split("-") if season else []
    season_year1 = season_parts[0] if len(season_parts) == 2 else str(target_year)
    season_year2 = season_parts[1] if len(season_parts) == 2 else str(target_year)

    def _render(text: str) -> str:
        return (
            text
            .replace("{year}", str(target_year))
            .replace("{season}", season or str(target_year))
            .replace("{season_year1}", season_year1)
            .replace("{season_year2}", season_year2)
            .replace("{today}", today.strftime("%Y-%m-%d"))
        )

    # Support single query (search_query) or multiple (search_queries)
    queries = venue.get("search_queries") or ([venue["search_query"]] if venue.get("search_query") else [])
    for query in queries:
        query = _render(query)
        print(f"  Searching: {query}")
        try:
            content = search_events(query, max_results=5)
            if content:
                parts.append(content)
        except Exception as e:
            print(f"  Warning: search failed: {e}")

    render_js = venue.get("render_js", True)
    provider = venue.get("fetch_provider", "auto")  # "auto", "linkup", "tavily"
    urls = [_render(u) for u in venue.get("urls", [])]
    if urls:
        label = f"[{provider}]" if provider != "auto" else ("[JS rendering]" if render_js else "")
        print(f"  Fetching {len(urls)} URL(s) {label}...")
        try:
            url_content = fetch_urls(urls, render_js=render_js, provider=provider)
            if url_content:
                parts.append(url_content)
        except Exception as e:
            print(f"  Warning: URL fetch failed: {e}")

    return "\n\n===\n\n".join(parts)


def get_venue_info(venue: dict) -> str:
    """Get raw content for venue static info (for MD generation)."""
    try:
        return search_events(venue["md_search_query"], max_results=3)
    except Exception as e:
        print(f"  Warning: venue info search failed: {e}")
        return ""
