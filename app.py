import tempfile

import gradio as gr

from agent import respond
from agent.elevenlabs_tts import list_voices, speak
from agent.voxtral import transcribe

_voices = list_voices()
VOICE_CHOICES = [(v.get("name") or v.get("voice_id", ""), v.get("voice_id", "")) for v in _voices] if _voices else [("Par défaut", "")]

PROVIDERS = ["mistral", "vllm", "nvidia"]
MODELS = {
    "mistral": ["ministral-8b-latest", "mistral-large-latest", "mistral-small-latest"],
    "vllm": [],
    "nvidia": ["meta/llama-3.1-70b-instruct", "mistralai/mistral-large"],
}

SUGGESTIONS = [
    "🎵 Concerts ce weekend",
    "🖼 Expositions en cours",
    "🎭 Agenda du Grimaldi Forum",
    "🎪 Événements gratuits",
]


def _to_messages(history):
    out = []
    for msg in history or []:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            out.append(msg)
        elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
            out.append({"role": "user", "content": msg[0]})
            if msg[1]:
                out.append({"role": "assistant", "content": msg[1]})
    return out


def _messages_to_chatbot_format(messages):
    return [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in (messages or [])]


def _tts_to_file(text, voice_id=None):
    if not (text or "").strip():
        return None
    raw = speak(text.strip(), voice_id=voice_id or None)
    if not raw:
        return None
    suffix = ".mp3"
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.write(raw)
    f.close()
    return f.name


def handle_voice(audio_path, history, provider, model, voice_id):
    if not audio_path:
        return history, None, None, ""
    transcript = (transcribe(audio_path) or "").strip()
    if not transcript:
        return history, None, None, ""
    messages = _to_messages(history)
    messages.append({"role": "user", "content": transcript})
    response = respond(transcript, history, provider=provider, model=model or None)
    messages.append({"role": "assistant", "content": response})
    new_chat = _messages_to_chatbot_format(messages)
    tts_path = _tts_to_file(response, voice_id)
    last_response = response
    return new_chat, None, tts_path, last_response


def handle_text(message, history, provider, model):
    if not (message or "").strip():
        return history, "", ""
    messages = _to_messages(history)
    messages.append({"role": "user", "content": message.strip()})
    response = respond(message.strip(), history, provider=provider, model=model or None)
    messages.append({"role": "assistant", "content": response})
    new_chat = _messages_to_chatbot_format(messages)
    return new_chat, "", response


def handle_listen(last_response, voice_id):
    if not (last_response or "").strip():
        return None
    return _tts_to_file(last_response, voice_id)


MONACO_CSS = """
:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #111111;
  --bg-tertiary: #1a1a1a;
  --accent-red: #e8002d;
  --accent-gold: #c9a84c;
  --accent-gold-light: #e8c870;
  --text-primary: #f5f5f5;
  --text-secondary: #888888;
  --border: #2a2a2a;
}

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&family=Rajdhani:wght@500;600;700&display=swap');

.gradio-container {
  font-family: 'Inter', sans-serif !important;
  background: var(--bg-primary) !important;
}

.gradio-container::before {
  content: "";
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
}

header.monaco-header {
  font-family: 'Rajdhani', sans-serif !important;
  background: var(--bg-primary) !important;
  padding: 1rem 1.5rem !important;
  border-bottom: 2px solid var(--accent-red) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
}

header.monaco-header h1 {
  font-family: 'Rajdhani', sans-serif !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  margin: 0 !important;
  font-size: 1.5rem !important;
  letter-spacing: 0.02em !important;
}

#monaco-sidebar {
  width: 260px !important;
  min-width: 260px !important;
  background: var(--bg-secondary) !important;
  padding: 1rem !important;
  border-radius: 4px !important;
  box-shadow: 0 4px 24px rgba(232, 0, 45, 0.08) !important;
}

#monaco-sidebar .block label {
  color: var(--text-secondary) !important;
  font-family: 'Inter', sans-serif !important;
}

#monaco-sidebar .gr-dropdown, #monaco-sidebar input {
  background: var(--bg-tertiary) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: 4px !important;
}

#monaco-sidebar .gr-dropdown:focus-within, #monaco-sidebar input:focus {
  border-color: var(--accent-red) !important;
  outline: none !important;
}

.about-block {
  color: var(--text-secondary) !important;
  font-size: 0.9rem !important;
  margin-top: 1rem !important;
  padding-top: 1rem !important;
  border-top: 1px solid var(--border) !important;
}

.about-block h3 {
  color: var(--accent-gold) !important;
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 1rem !important;
  margin-bottom: 0.5rem !important;
}

#chat-container .message {
  animation: msgFadeIn 200ms ease-out forwards;
}

@keyframes msgFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

#chat-container .message.user .message-body,
#chat-container [data-testid="user"] .message-body {
  background: #1a1a1a !important;
  border-left: 3px solid var(--accent-red) !important;
  color: var(--text-primary) !important;
  border-radius: 4px !important;
}

#chat-container .message.bot .message-body,
#chat-container [data-testid="assistant"] .message-body {
  background: var(--bg-secondary) !important;
  border-left: 3px solid var(--accent-gold) !important;
  color: var(--text-primary) !important;
  border-radius: 4px !important;
}

#input-row .gr-box {
  background: var(--bg-tertiary) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: 4px !important;
}

#input-row .gr-box:focus-within {
  border-color: var(--accent-red) !important;
}

#send_btn.primary-btn {
  background: var(--accent-red) !important;
  color: white !important;
  border: none !important;
  border-radius: 4px !important;
  font-family: 'Rajdhani', sans-serif !important;
  font-weight: 600 !important;
  transition: background 150ms, transform 150ms !important;
}

#send_btn.primary-btn:hover {
  background: #ff1a47 !important;
  transform: translateY(-1px) !important;
}

#listen_btn {
  background: transparent !important;
  border: 1px solid var(--accent-gold) !important;
  color: var(--accent-gold) !important;
  border-radius: 4px !important;
  transition: border-color 150ms, color 150ms !important;
}

#listen_btn:hover:not([disabled]) {
  border-color: var(--accent-gold-light) !important;
  color: var(--accent-gold-light) !important;
}

#mic_trigger_wrapper {
  position: relative !important;
  width: 52px !important;
  height: 52px !important;
  flex-shrink: 0 !important;
}

#mic_trigger {
  width: 52px !important;
  height: 52px !important;
  border-radius: 50% !important;
  background: var(--bg-tertiary) !important;
  border: 2px solid var(--border) !important;
  color: var(--text-primary) !important;
  font-size: 1.5rem !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  transition: border-color 150ms, background 150ms !important;
  position: relative !important;
  z-index: 2 !important;
}

#mic_trigger:hover {
  border-color: var(--accent-red) !important;
  background: var(--bg-secondary) !important;
}

#mic_trigger.recording {
  background: var(--accent-red) !important;
  border-color: var(--accent-red) !important;
  animation: micPulse 1.2s ease-in-out infinite !important;
}

#mic_trigger.recording::after {
  content: "" !important;
  position: absolute !important;
  inset: -4px !important;
  border-radius: 50% !important;
  border: 2px solid var(--accent-red) !important;
  opacity: 0.6 !important;
  animation: micRing 1.2s ease-out infinite !important;
}

@keyframes micPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}

@keyframes micRing {
  0% { transform: scale(0.95); opacity: 0.6; }
  100% { transform: scale(1.15); opacity: 0; }
}

.recording-indicator {
  position: absolute !important;
  bottom: -22px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  font-size: 0.7rem !important;
  color: var(--accent-red) !important;
  white-space: nowrap !important;
  opacity: 0 !important;
  pointer-events: none !important;
  z-index: 1 !important;
}

.recording-indicator.visible {
  opacity: 1 !important;
  animation: dotPulse 0.6s ease-in-out infinite !important;
}

@keyframes dotPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

#audio_mic_wrap {
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  width: 52px !important;
  height: 52px !important;
  overflow: hidden !important;
  border-radius: 50% !important;
  z-index: 1 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

#audio_mic_wrap * {
  pointer-events: auto !important;
}

#audio_mic_wrap .gr-audio {
  width: 100% !important;
  height: 100% !important;
  min-height: unset !important;
}

#suggestions_container .suggestion-btn {
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: 4px !important;
  padding: 0.6rem 1rem !important;
  font-family: 'Inter', sans-serif !important;
  transition: border-color 150ms, color 150ms !important;
}

#suggestions_container .suggestion-btn:hover {
  border-color: var(--accent-gold) !important;
  color: var(--accent-gold-light) !important;
}

#chat-container .gr-block {
  background: var(--bg-primary) !important;
}

#chat-container::-webkit-scrollbar {
  width: 8px !important;
}

#chat-container::-webkit-scrollbar-track {
  background: var(--bg-secondary) !important;
  border-radius: 4px !important;
}

#chat-container::-webkit-scrollbar-thumb {
  background: var(--accent-red) !important;
  border-radius: 4px !important;
}

.status-dots {
  display: inline-flex !important;
  gap: 4px !important;
}

.status-dots span {
  width: 6px !important;
  height: 6px !important;
  background: var(--accent-gold) !important;
  border-radius: 50% !important;
  animation: statusBounce 0.6s ease-in-out infinite !important;
}

.status-dots span:nth-child(2) { animation-delay: 0.1s !important; }
.status-dots span:nth-child(3) { animation-delay: 0.2s !important; }

@keyframes statusBounce {
  0%, 100% { transform: translateY(0); opacity: 0.6; }
  50% { transform: translateY(-4px); opacity: 1; }
}

#audio_out_container .gr-audio {
  max-height: 48px !important;
}

#audio_out_container audio {
  border-radius: 4px !important;
}
"""

MONACO_JS = """
function setupMicTrigger() {
  const wrapper = document.getElementById('mic_trigger_wrapper');
  const trigger = document.getElementById('mic_trigger');
  const indicator = document.querySelector('.recording-indicator');
  const audioWrap = document.getElementById('audio_mic_wrap');
  if (!wrapper || !trigger) return;

  let recording = false;
  trigger.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    if (!audioWrap) return;
    const btn = audioWrap.querySelector('button');
    if (btn) {
      btn.click();
      recording = !recording;
      trigger.classList.toggle('recording', recording);
      if (indicator) indicator.classList.toggle('visible', recording);
    }
  });
}

document.addEventListener('DOMContentLoaded', function() {
  setTimeout(setupMicTrigger, 500);
});

if (document.readyState !== 'loading') {
  setTimeout(setupMicTrigger, 500);
}
"""


with gr.Blocks(title="Monaco Cultural Agent", css=MONACO_CSS, js=MONACO_JS, theme=gr.themes.Base()) as demo:
    last_response = gr.State("")

    gr.HTML(
        '<header class="monaco-header">'
        '<h1>🏎 MONACO CULTURAL AGENT</h1>'
        '<span style="color: var(--text-secondary); font-size: 0.9rem;">Settings</span>'
        '</header>'
    )

    with gr.Row():
        with gr.Column(scale=1, min_width=200):
            chatbot = gr.Chatbot(
                elem_id="chat-container",
                height=400,
                show_label=False,
                container=True,
            )
            suggestions_container = gr.Row(elem_id="suggestions_container", visible=True)
            suggestion_btns = []
            with suggestions_container:
                for sug in SUGGESTIONS:
                    b = gr.Button(sug, elem_classes=["suggestion-btn"], size="sm")
                    suggestion_btns.append(b)

            with gr.Row(elem_id="input-row"):
                msg_in = gr.Textbox(
                    placeholder="Écrivez votre question…",
                    show_label=False,
                    container=False,
                    scale=4,
                )
                with gr.Column(scale=0, min_width=60):
                    with gr.Column(elem_id="mic_trigger_wrapper"):
                        gr.HTML('<span class="recording-indicator">Enregistrement…</span>')
                        with gr.Column(elem_id="audio_mic_wrap"):
                            audio_mic = gr.Audio(
                                sources=["microphone"],
                                type="filepath",
                                streaming=False,
                                show_label=False,
                                elem_id="audio_mic",
                            )
                        mic_btn = gr.Button("🎙", elem_id="mic_trigger")
                send_btn = gr.Button("Envoyer", elem_id="send_btn", elem_classes=["primary-btn"], scale=1)
            listen_btn = gr.Button("🔊 Écouter", elem_id="listen_btn", visible=True, interactive=False)
            with gr.Row(elem_id="audio_out_container"):
                audio_out = gr.Audio(show_label=False, autoplay=True, visible=True, elem_id="audio_out")

        with gr.Column(elem_id="monaco-sidebar", scale=0, min_width=260):
            gr.Markdown("**⚙ Paramètres**")
            provider_dd = gr.Dropdown(PROVIDERS, value="mistral", label="Provider")
            model_dd = gr.Dropdown(MODELS["mistral"], value="ministral-8b-latest", label="Modèle")
            provider_dd.change(
                fn=lambda p: gr.Dropdown(choices=MODELS.get(p, []), value=(MODELS.get(p, [""])[0] or None)),
                inputs=provider_dd,
                outputs=model_dd,
            )
            gr.Markdown("---")
            with gr.Column(elem_classes=["about-block"]):
                gr.Markdown("### 📍 À propos")
                gr.Markdown("Agent spécialisé culture et événements à Monaco.")

            if VOICE_CHOICES:
                voice_dd = gr.Dropdown(choices=VOICE_CHOICES, value=(VOICE_CHOICES[0][1] if VOICE_CHOICES else ""), label="Voix TTS")
            else:
                voice_dd = gr.Dropdown(choices=[], value="", label="Voix TTS", visible=False)

    def make_suggestion_fn(sug_text):
        def fn(hist, prov, mod):
            new_chat, _, last = handle_text(sug_text, hist, prov, mod)
            return new_chat, "", last, gr.update(visible=False), gr.update(interactive=True)
        return fn

    for sug, b in zip(SUGGESTIONS, suggestion_btns):
        b.click(
            fn=make_suggestion_fn(sug),
            inputs=[chatbot, provider_dd, model_dd],
            outputs=[chatbot, msg_in, last_response, suggestions_container, listen_btn],
        )

    def voice_handler(audio_path, hist, prov, mod, vid):
        new_chat, _, tts_path, last = handle_voice(audio_path, hist, prov, mod, vid)
        return (new_chat, gr.update(value=None), gr.update(value=tts_path, autoplay=bool(tts_path)),
                last, gr.update(visible=(len(new_chat) == 0)), gr.update(interactive=True))

    audio_mic.change(
        fn=voice_handler,
        inputs=[audio_mic, chatbot, provider_dd, model_dd, voice_dd],
        outputs=[chatbot, audio_mic, audio_out, last_response, suggestions_container, listen_btn],
    )

    def text_handler(msg, hist, prov, mod):
        new_chat, clear, last = handle_text(msg, hist, prov, mod)
        return new_chat, clear, last, gr.update(visible=False), gr.update(interactive=True)

    send_btn.click(
        fn=text_handler,
        inputs=[msg_in, chatbot, provider_dd, model_dd],
        outputs=[chatbot, msg_in, last_response, suggestions_container, listen_btn],
    )
    msg_in.submit(
        fn=text_handler,
        inputs=[msg_in, chatbot, provider_dd, model_dd],
        outputs=[chatbot, msg_in, last_response, suggestions_container, listen_btn],
    )

    def listen_handler(last, vid):
        path = handle_listen(last, vid)
        return gr.update(value=path, autoplay=bool(path))

    listen_btn.click(
        fn=listen_handler,
        inputs=[last_response, voice_dd],
        outputs=audio_out,
    )

    def toggle_suggestions(history):
        return gr.update(visible=len(history) == 0)

    chatbot.change(fn=toggle_suggestions, inputs=[chatbot], outputs=[suggestions_container])


if __name__ == "__main__":
    demo.launch()
