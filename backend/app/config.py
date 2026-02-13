"""
Blueprint Backend — Central Configuration

All environment variables and LLM settings live here.
Import `settings`, `LLM_CONFIG`, `log`, and `generate_error_code` from this module.
Do not read `os.environ` anywhere else.
"""

import uuid
from datetime import datetime, timezone

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All environment variables. Loaded from .env or Railway env vars."""

    # LLM Providers
    gemini_api_key: str
    openai_api_key: str = ""          # Optional fallback
    anthropic_api_key: str = ""       # Optional fallback

    # Search
    tavily_api_key: str              # Tavily Search API — primary web + Reddit search
    serper_api_key: str = ""         # Serper API — fallback search provider (recommended)

    # Scraping
    jina_api_key: str = ""            # Optional — Jina works without key at lower rate

    # Database
    supabase_url: str
    supabase_service_key: str

    # App
    environment: str = "development"  # "development" | "production"
    cors_origins: str = "http://localhost:3000"  # Comma-separated for multiple origins

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton — import this everywhere
settings = Settings()


# ──────────────────────────────────────────────────────
# Logging Utilities (V0 — structured print, replaced by structlog in V1)
# ──────────────────────────────────────────────────────

def generate_error_code() -> str:
    """Generate a short, user-friendly error reference code.

    Format: 'BP-' followed by 6 uppercase hex characters.
    Example: 'BP-3F8A2C'

    Used whenever an error is surfaced to the user (via ErrorEvent or BlockErrorEvent SSE).
    The same code is logged on the backend AND sent to the user, so the user can
    quote it and the team can grep logs for it.
    """
    return f"BP-{uuid.uuid4().hex[:6].upper()}"


def log(level: str, message: str, **context) -> None:
    """Structured print-based logger for V0.

    Every log line follows the format:
        [ISO_TIMESTAMP] [LEVEL] message | key1=value1 key2=value2

    Args:
        level: One of "INFO", "WARN", "ERROR".
        message: Human-readable description of what happened.
        **context: Arbitrary key-value pairs. Always include journey_id when available.

    Usage:
        log("INFO", "pipeline started", journey_id="abc-123", pipeline="classify")
        log("ERROR", "llm call failed", journey_id="abc-123", provider="gemini",
            error_code="BP-3F8A2C", error=str(e))
    """
    ts = datetime.now(timezone.utc).isoformat()
    ctx = " ".join(f"{k}={v}" for k, v in context.items())
    print(f"[{ts}] [{level}] {message} | {ctx}", flush=True)


# ──────────────────────────────────────────────────────
# LLM Configuration
# ──────────────────────────────────────────────────────

# LLM Configuration (see ARCHITECTURE.md ADR-2 and ADR-3)
LLM_CONFIG = {
    "persona": {
        "name": "Blueprint",
        "system_prompt": (
            "You are Blueprint, a product and market research assistant for B2C software. "
            "You help product managers and founders explore competitive landscapes, identify market gaps, "
            "and define focused problem statements.\n\n"
            "Guidelines:\n"
            "- Be concise and structured. Use bullet points for features and comparisons.\n"
            "- Always cite sources when referencing specific data. If information is unavailable, say so — never fabricate.\n"
            "- Output strictly valid JSON when instructed. No markdown code fences, no explanation text outside the JSON.\n"
            "- Stay within your domain: product strategy, market research, and competitive analysis. "
            "Decline requests for code generation, homework, creative writing, or general knowledge.\n"
            "- When analyzing products, be balanced — acknowledge both strengths and weaknesses.\n"
            "- Ground all claims in provided data. Do not speculate beyond what the evidence supports."
        ),
    },
    "temperature": 0.3,
    "max_tokens": 2000,
    "fallback_chain": [
        "gemini/gemini-2.5-pro",         # Primary — newest, best quality
        "gemini/gemini-2.5-flash",       # Fallback 1 — fast + cheap
        "gemini/gemini-2.0-flash",       # Fallback 2 — free tier
        "openai/gpt-4o-mini",            # Fallback 3 — non-Google fallback
        "anthropic/claude-3-haiku",      # Fallback 4 — last resort
    ],
}
