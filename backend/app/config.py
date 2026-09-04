import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # --- LLM provider config -------------------------------------------------
    # Provider abstraction: swap via LLM_PROVIDER without touching call sites.
    # "anthropic" is the only provider reachable/testable from the environment
    # this project was scaffolded in; groq/gemini/openrouter are implemented
    # against their documented REST APIs but untested here for that reason.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

    # --- storage ---------------------------------------------------------------
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "boardmind.db")
    DUCKDB_PATH: str = os.getenv("DUCKDB_PATH", ":memory:")

    DATA_SEED: int = int(os.getenv("DATA_SEED", "20260822"))
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    # Permit HTTPS deployments by default; restrict this further with
    # CORS_ORIGINS or CORS_ORIGIN_REGEX when the API is used privately.
    CORS_ORIGIN_REGEX: str = os.getenv("CORS_ORIGIN_REGEX", "").strip() or (
        r"https://([a-z0-9-]+\.)+[a-z]{2,}|https://localhost(:\d+)?"
    )

settings = Settings()

def llm_configured() -> bool:
    provider = settings.LLM_PROVIDER
    return bool({
        "anthropic": settings.ANTHROPIC_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
    }.get(provider, ""))
