import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from agent import respond
from agent.elevenlabs_tts import list_voices, speak
from agent.voxtral import transcribe
from agent import get_last_scraped_at

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    history: list
    provider: str = "mistral"
    model: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/chat")
async def chat(body: ChatRequest):
    try:
        out = respond(
            body.message,
            body.history,
            provider=body.provider,
            model=body.model,
        )
        if isinstance(out, dict):
            return out
        return {"response": out or ""}
    except Exception as e:
        return {"response": f"Désolé, une erreur s'est produite : {e}"}


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    path = None
    try:
        suffix = Path(file.filename or "").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            path = tmp.name
        text = (transcribe(path) or "").strip()
        return {"text": text}
    except Exception:
        return {"text": ""}
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


@app.post("/tts")
async def text_to_speech(body: TTSRequest):
    if not (body.text or "").strip():
        return Response(status_code=400, content="Empty text")
    raw = speak(body.text.strip(), voice_id=body.voice_id or None)
    if not raw:
        return Response(status_code=503, content="TTS unavailable")
    return Response(content=raw, media_type="audio/mpeg")


@app.get("/voices")
async def voices():
    try:
        return list_voices()
    except Exception:
        return []


@app.get("/last-scraped")
async def last_scraped():
    return {"last_scraped_at": get_last_scraped_at()}


app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=True)
