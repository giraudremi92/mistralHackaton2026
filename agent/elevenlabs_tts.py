import os

import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_VOICES_URL = "https://api.elevenlabs.io/v1/voices"
DEFAULT_VOICE_ID = "TX3LPaxmHKxFdv7VOQHJ"
MODEL_ID = "eleven_multilingual_v2"


def get_voice_id(api_key: str | None = None, voice_id: str | None = None) -> str:
    return (
        voice_id
        or (os.getenv("ELEVENLABS_VOICE_ID") or "").strip()
        or DEFAULT_VOICE_ID
    )


def list_voices(api_key: str | None = None) -> list[dict]:
    api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        return []
    try:
        r = requests.get(ELEVENLABS_VOICES_URL, headers={"xi-api-key": api_key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("voices", [])
    except (requests.RequestException, KeyError):
        return []


def speak(text: str, api_key: str | None = None, voice_id: str | None = None) -> bytes | None:
    if not (text or "").strip():
        return None
    api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        return None
    voice_id = get_voice_id(api_key, voice_id)
    url = f"{ELEVENLABS_URL}/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {"text": text.strip(), "model_id": MODEL_ID}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException:
        return None
    if not r.content:
        return None
    return r.content
