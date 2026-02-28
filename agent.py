from pathlib import Path
from providers import chat

CONTEXT_FILES = ["SYSTEM_PROMPT.md", "MEMORY.md"]


def load_context() -> str:
    """Load system context from MD files (reloaded on every call)."""
    parts = []
    for fname in CONTEXT_FILES:
        p = Path(fname)
        if p.exists():
            parts.append(f"# {fname}\n{p.read_text()}")
    return "\n\n".join(parts)


def respond(message: str, history: list, provider: str = "mistral", model: str | None = None) -> str:
    """Build messages from history + context, call LLM, return response."""
    messages = [{"role": "system", "content": load_context()}]

    for msg in history:
        if isinstance(msg, dict):
            messages.append({"role": msg["role"], "content": msg["content"]})
        else:
            user_msg, assistant_msg = msg
            messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})

    messages.append({"role": "user", "content": message})
    return chat(messages, provider=provider, model=model or None)
