"""LLM factory: Groq (free), Ollama (local/free), optional OpenAI."""

from __future__ import annotations

import httpx
from langchain_openai import ChatOpenAI

from backend.app.config import get_settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _ollama_available(base_url: str) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def resolve_llm_provider() -> str:
    """Return groq | ollama | openai | local."""
    settings = get_settings()
    requested = (settings.llm_provider or "auto").strip().lower()
    if requested in {"groq", "ollama", "openai", "local"}:
        return requested
    if settings.groq_api_key:
        return "groq"
    if _ollama_available(settings.ollama_base_url):
        return "ollama"
    if settings.openai_api_key:
        return "openai"
    return "local"


def build_llm():
    """Build a chat model that supports tool calling, or None for local (no-LLM) mode."""
    settings = get_settings()
    provider = resolve_llm_provider()

    if provider == "local":
        return None

    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is empty. "
                "Get a free key at https://console.groq.com/keys"
            )
        return ChatOpenAI(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
            temperature=0.2,
            max_tokens=2048,
        )

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.2,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is empty.")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )

    raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")
