import gradio as gr
from agent import respond

PROVIDERS = ["mistral", "vllm", "nvidia", "lmstudio"]

MODELS = {
    "mistral": ["ministral-8b-latest", "mistral-large-latest", "mistral-small-latest"],
    "vllm": [],
    "nvidia": ["mistralai/ministral-14b-instruct-2512"],
    "lmstudio": ["ministral-3-14b-instruct-2512"],
}


def chat_fn(message, history, provider, model):
    return respond(message, history, provider=provider, model=model or None)


def reload_status():
    return "Context reloaded from MD files."


with gr.Blocks(title="NanoAgent") as demo:
    gr.Markdown("# NanoAgent")

    provider_dd = gr.Dropdown(PROVIDERS, value="mistral", label="Provider")
    model_dd = gr.Dropdown(MODELS["mistral"], value="ministral-8b-latest", label="Model")

    provider_dd.change(
        fn=lambda p: gr.Dropdown(choices=MODELS.get(p, []), value=(MODELS.get(p) or [None])[0]),
        inputs=provider_dd,
        outputs=model_dd,
    )

    gr.ChatInterface(
        fn=chat_fn,
        additional_inputs=[provider_dd, model_dd],
        chatbot=gr.Chatbot(height=500),
        additional_inputs_accordion=gr.Accordion("Settings", open=True),
    )

    with gr.Row():
        reload_btn = gr.Button("Reload SYSTEM_PROMPT.md / MEMORY.md")
        status = gr.Textbox(label="", interactive=False, scale=3)

    reload_btn.click(reload_status, outputs=status)


if __name__ == "__main__":
    demo.launch()
