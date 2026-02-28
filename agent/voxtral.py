import os
import tempfile
import wave
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

VOXTRAL_URL = "https://api.mistral.ai/v1/audio/transcriptions"
VOXTRAL_MODEL = "voxtral-mini-latest"


def _write_ndarray_to_wav(sample_rate: int, data, path: str) -> None:
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1 if data.ndim == 1 else data.shape[1])
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        if data.dtype.kind == "f":
            data = (data * 32767).astype("int16")
        wav.writeframes(data.tobytes())


def transcribe(audio_input: str | tuple | dict | None, api_key: str | None = None) -> str:
    if audio_input is None:
        return ""
    api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        return ""
    path = None
    if isinstance(audio_input, str):
        path = audio_input
    elif isinstance(audio_input, dict) and audio_input.get("path"):
        path = audio_input["path"]
    elif isinstance(audio_input, tuple) and len(audio_input) == 2:
        sample_rate, data = audio_input
        try:
            import numpy as np
            if not isinstance(data, np.ndarray):
                return ""
        except ImportError:
            return ""
        fd, path = tempfile.mkstemp(suffix=".wav")
        try:
            _write_ndarray_to_wav(sample_rate, data, path)
        finally:
            os.close(fd)
    else:
        return ""
    if not path or not Path(path).exists():
        return ""
    try:
        with open(path, "rb") as f:
            files = {"file": (Path(path).name, f, "audio/wav")}
            data = {"model": VOXTRAL_MODEL}
            r = requests.post(
                VOXTRAL_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
                timeout=60,
            )
        r.raise_for_status()
        out = r.json()
        return (out.get("text") or "").strip()
    except (requests.RequestException, KeyError):
        return ""
    finally:
        if isinstance(audio_input, tuple) and path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
