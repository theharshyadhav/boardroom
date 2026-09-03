from fastapi import APIRouter
from ..llm_provider import TELEMETRY, estimated_cost_usd
from ..config import settings, llm_configured

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

@router.get("")
def get_telemetry():
    avg_latency = round(TELEMETRY["total_latency_ms"] / TELEMETRY["calls"]) if TELEMETRY["calls"] else 0
    return {
        "provider": settings.LLM_PROVIDER,
        "model": {"anthropic": settings.ANTHROPIC_MODEL, "groq": settings.GROQ_MODEL,
                   "gemini": settings.GEMINI_MODEL, "openrouter": settings.OPENROUTER_MODEL}[settings.LLM_PROVIDER],
        "configured": llm_configured(),
        "calls": TELEMETRY["calls"],
        "cacheHits": TELEMETRY["cache_hits"],
        "avgLatencyMs": avg_latency,
        "inputTokens": TELEMETRY["in_tokens"],
        "outputTokens": TELEMETRY["out_tokens"],
        "estimatedCostUsd": round(estimated_cost_usd(), 6),
        "log": TELEMETRY["log"],
    }
