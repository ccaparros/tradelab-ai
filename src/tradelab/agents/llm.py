"""OpenAI-compatible LLM client (DeepSeek default)."""

from __future__ import annotations

import json
from typing import Any

from tradelab.observability.settings import get_settings


def llm_configured() -> bool:
    s = get_settings()
    return bool(s.llm_api_key.strip())


def chat_completion(
    *,
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    """Call OpenAI-compatible Chat Completions API (DeepSeek, OpenAI, Azure-compatible gateways)."""
    import httpx
    from openai import OpenAI

    s = get_settings()
    if not s.llm_api_key.strip():
        raise RuntimeError("LLM_API_KEY not configured")

    base_url = (s.llm_base_url or "https://api.deepseek.com").rstrip("/")
    model = s.llm_model or "deepseek-v4-flash"
    http_client = httpx.Client(verify=s.llm_ssl_verify, timeout=60.0)
    client = OpenAI(api_key=s.llm_api_key, base_url=base_url, http_client=http_client)

    # Disable thinking for stable JSON synthesis (metrics already come from tools).
    create_kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    if model.startswith("deepseek-v4"):
        create_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    resp = client.chat.completions.create(**create_kwargs)
    content = resp.choices[0].message.content or "{}"
    usage = None
    if resp.usage:
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
        }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {
            "answer": content,
            "assumptions": [],
            "warnings": ["LLM returned non-JSON"],
            "confidence": 0.4,
        }
    return {
        "parsed": parsed,
        "raw": content,
        "model": model,
        "base_url": base_url,
        "usage": usage,
    }
