"""
10. LLM NARRATIVE LAYER — the ONLY module allowed to call a model.
It never computes numbers; it only narrates numbers already produced by the
deterministic layers above. If no API key is configured, or the call fails
for any reason, callers fall back to a deterministic templated narrative so
the product is always demoable.
"""
import time
import json
import httpx
from .config import settings, llm_configured

TELEMETRY = {"calls": 0, "cache_hits": 0, "in_tokens": 0, "out_tokens": 0, "total_latency_ms": 0, "log": []}
_CACHE: dict[str, str] = {}


def _log(entry: dict):
    TELEMETRY["log"].insert(0, entry)
    TELEMETRY["log"][:] = TELEMETRY["log"][:12]


async def _call_anthropic(system: str, user: str, max_tokens: int) -> tuple[str | None, dict]:
    headers = {"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    body = {"model": settings.ANTHROPIC_MODEL, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": user}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
        data = resp.json()
        if resp.status_code != 200 or "content" not in data:
            return None, {}
        text = "\n".join(b["text"] for b in data["content"] if b.get("type") == "text")
        return text, data.get("usage", {})


async def _call_groq(system: str, user: str, max_tokens: int) -> tuple[str | None, dict]:
    # Groq's Chat Completions API is OpenAI-compatible. Implemented per the
    # brief's provider priority; untested in this environment since
    # api.groq.com is not reachable from the sandbox this project was built in.
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "content-type": "application/json"}
    body = {"model": settings.GROQ_MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
        data = resp.json()
        if resp.status_code != 200 or "choices" not in data:
            return None, {}
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}


async def _call_gemini(system: str, user: str, max_tokens: int) -> tuple[str | None, dict]:
    # Untested here for the same reachability reason as Groq.
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
           f"?key={settings.GEMINI_API_KEY}")
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body)
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return None, {}
        usage_meta = data.get("usageMetadata", {})
        return text, {"input_tokens": usage_meta.get("promptTokenCount", 0),
                      "output_tokens": usage_meta.get("candidatesTokenCount", 0)}


async def _call_openrouter(system: str, user: str, max_tokens: int) -> tuple[str | None, dict]:
    headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "content-type": "application/json"}
    body = {"model": settings.OPENROUTER_MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
        data = resp.json()
        if resp.status_code != 200 or "choices" not in data:
            return None, {}
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}


_PROVIDERS = {"anthropic": _call_anthropic, "groq": _call_groq, "gemini": _call_gemini, "openrouter": _call_openrouter}


async def call_llm(system: str, user: str, max_tokens: int = 500) -> str | None:
    cache_key = f"{settings.LLM_PROVIDER}:{hash(system+user)}"
    if cache_key in _CACHE:
        TELEMETRY["cache_hits"] += 1
        _log({"ts": time.strftime("%H:%M:%S"), "cached": True, "latency": 0})
        return _CACHE[cache_key]

    if not llm_configured():
        _log({"ts": time.strftime("%H:%M:%S"), "cached": False, "ok": False, "reason": "no API key configured"})
        return None

    fn = _PROVIDERS.get(settings.LLM_PROVIDER)
    t0 = time.perf_counter()
    try:
        text, usage = await fn(system, user, max_tokens)
    except Exception:
        text, usage = None, {}
    latency = round((time.perf_counter() - t0) * 1000)

    TELEMETRY["calls"] += 1
    TELEMETRY["in_tokens"] += usage.get("input_tokens", 0)
    TELEMETRY["out_tokens"] += usage.get("output_tokens", 0)
    TELEMETRY["total_latency_ms"] += latency
    _log({"ts": time.strftime("%H:%M:%S"), "cached": False, "ok": text is not None, "latency": latency,
          "inTok": usage.get("input_tokens", 0), "outTok": usage.get("output_tokens", 0)})

    if text is None:
        return None
    _CACHE[cache_key] = text
    return text


def estimated_cost_usd() -> float:
    # Anthropic Sonnet-class pricing used as the estimate basis regardless of
    # active provider, since Groq/Gemini free tiers don't have a stable
    # equivalent to quote — labelled "estimated" in the UI for that reason.
    return TELEMETRY["in_tokens"] / 1e6 * 3 + TELEMETRY["out_tokens"] / 1e6 * 15
