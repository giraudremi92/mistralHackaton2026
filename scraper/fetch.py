"""Fetch raw content using Tavily search + fetch."""

import os
from datetime import date
from typing import Any

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


def get_client() -> Any:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY not set in environment.")
    if not TAVILY_AVAILABLE:
        raise ImportError("tavily-python not installed. Run: pip install tavily-python")
    return TavilyClient(api_key=api_key)


def search_events(query: str, max_results: int = 5) -> str:
    """Search web for events and return concatenated content."""
    client = get_client()
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


def fetch_urls(urls: list[str]) -> str:
    """Fetch specific URLs and return concatenated content."""
    client = get_client()
    parts = []
    for url in urls:
        try:
            result = client.extract(urls=[url])
            for r in result.get("results", []):
                content = r.get("raw_content") or r.get("content", "")
                if content:
                    parts.append(f"[Source: {url}]\n{content}")
        except Exception as e:
            print(f"  Warning: could not fetch {url}: {e}")
    return "\n\n---\n\n".join(parts)


def get_raw_content(venue: dict) -> str:
    """Get raw content for a venue using search + direct URL fetch."""
    parts = []

    # Support single query (search_query) or multiple (search_queries)
    queries = venue.get("search_queries") or ([venue["search_query"]] if venue.get("search_query") else [])
    for query in queries:
        print(f"  Searching: {query}")
        try:
            content = search_events(query, max_results=5)
            if content:
                parts.append(content)
        except Exception as e:
            print(f"  Warning: search failed: {e}")

    today = date.today().strftime("%Y-%m-%d")
    urls = [u.replace("{today}", today) for u in venue.get("urls", [])]
    if urls:
        print(f"  Fetching {len(urls)} URL(s)...")
        try:
            url_content = fetch_urls(urls)
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
