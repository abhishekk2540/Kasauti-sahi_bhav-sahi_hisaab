"""LLM access. Two providers behind one small surface:

- groq      : OpenAI-compatible API (default model openai/gpt-oss-20b). Client is `openai.OpenAI`.
- anthropic : Anthropic SDK.
Selected by LLM_PROVIDER, or automatically: groq if GROQ_API_KEY is set, else anthropic.
"""
import os

from ..config import get_settings

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


def is_openai_style(client) -> bool:
    return hasattr(client, "chat")


def model_name() -> str:
    s = get_settings()
    return s.groq_model if s.llm_provider == "groq" else s.anthropic_model


def get_llm_client():
    """Returns a configured client, or None when no API key is set."""
    s = get_settings()
    if s.llm_provider == "groq":
        if not s.groq_api_key:
            return None
        from openai import OpenAI

        return OpenAI(api_key=s.groq_api_key, base_url=GROQ_BASE_URL, timeout=30, max_retries=2)
    if not s.anthropic_api_key:
        return None
    import anthropic

    return anthropic.Anthropic(api_key=s.anthropic_api_key)


def simple_complete(client, system: str, user: str, max_tokens: int = 300) -> str:
    """One-shot text completion on either provider. Raises on API errors (callers decide the fallback)."""
    model = model_name()
    if is_openai_style(client):
        r = client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=0.3,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return (r.choices[0].message.content or "").strip()
    r = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                               messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
