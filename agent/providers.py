import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROVIDERS = {
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_key": os.getenv("MISTRAL_API_KEY", ""),
        "default_model": "mistral-large-latest",
    },
    "vllm": {
        "base_url": os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        "api_key": os.getenv("VLLM_API_KEY", "token-abc"),
        "default_model": os.getenv("VLLM_MODEL", ""),
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": os.getenv("NVIDIA_API_KEY", ""),
        "default_model": "meta/llama-3.1-70b-instruct",
    },
}


def chat(messages: list, provider: str = "mistral", model: str | None = None) -> str:
    cfg = PROVIDERS[provider]
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    response = client.chat.completions.create(
        model=model or cfg["default_model"],
        messages=messages,
    )
    return response.choices[0].message.content
