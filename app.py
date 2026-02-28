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


def submit(message, audio, history, provider, model, speaker_on, voice_id):
    content = ""
    if audio:
        content = (transcribe(audio) or "").strip()
    if not content and (message or "").strip():
        content = message.strip()
    if not content:
        return history, "", None, None
    messages = _to_messages(history)
    response = respond(content, messages, provider=provider, model=model or None)
    new_history = messages + [{"role": "user", "content": content}, {"role": "assistant", "content": response}]
    tts_path = None
    if speaker_on and response:
        tts_path = speak(response, voice_id=voice_id or None)
    return new_history, "", None, tts_path


with gr.Blocks(title="NanoAgent") as demo:
    gr.Markdown("# NanoAgent")

    provider_dd = gr.Dropdown(PROVIDERS, value="mistral", label="Provider")
    model_dd = gr.Dropdown(MODELS["mistral"], value="ministral-8b-latest", label="Model")

    provider_dd.change(
        fn=lambda p: gr.Dropdown(choices=MODELS.get(p, []), value=(MODELS.get(p, [""])[0])),
        inputs=provider_dd,
        outputs=model_dd,
    )

    chatbot = gr.Chatbot(height=500)

    with gr.Accordion("Settings", open=True):
        gr.Markdown("Provider et modèle ci-dessus.")
        speaker_on = gr.Checkbox(label="Lire la réponse à voix haute (ElevenLabs)", value=False)
        voice_dd = gr.Dropdown(choices=VOICE_CHOICES, value=(VOICE_CHOICES[0][1] if VOICE_CHOICES else ""), label="Voix ElevenLabs")

    with gr.Row():
        with gr.Column(scale=4):
            msg_in = gr.Textbox(placeholder="Écrivez ou enregistrez votre message (texte ou vocal, Voxtral)…", container=False, show_label=False)
            audio_in = gr.Audio(sources=["microphone", "upload"], type="filepath", format="wav", show_label=False)
        send_btn = gr.Button("Envoyer", scale=1)

    audio_out = gr.Audio(label="Réponse lue à voix haute", visible=True, autoplay=False)

    send_btn.click(
        fn=submit,
        inputs=[msg_in, audio_in, chatbot, provider_dd, model_dd, speaker_on, voice_dd],
        outputs=[chatbot, msg_in, audio_in, audio_out],
    )
    msg_in.submit(
        fn=submit,
        inputs=[msg_in, audio_in, chatbot, provider_dd, model_dd, speaker_on, voice_dd],
        outputs=[chatbot, msg_in, audio_in, audio_out],
    )


if __name__ == "__main__":
    demo.launch()
