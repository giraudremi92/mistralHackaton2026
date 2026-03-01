"""Load venue definitions from sources.json."""

import json
from pathlib import Path

_SOURCES_FILE = Path(__file__).parent / "sources.json"

VENUES: list[dict] = json.loads(_SOURCES_FILE.read_text(encoding="utf-8"))
