"""
Blueprint Backend — Database Operations

All Supabase/PostgreSQL operations: product cache, alternatives cache,
journey CRUD, LLM state, user choice logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from supabase import Client, create_client

from app.config import LLM_CONFIG, generate_error_code, log, settings

# ─────────────────────────────────────────────────────────────────────────────
# Supabase Client (singleton)
# ─────────────────────────────────────────────────────────────────────────────

_supabase: Client | None = None


def get_supabase() -> Client:
    """Return the Supabase client singleton. Creates it on first call."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase


# ─────────────────────────────────────────────────────────────────────────────
# Product Cache
# ─────────────────────────────────────────────────────────────────────────────


def normalize_product_name(name: str) -> str:
    """
    Normalize a product name for cache key lookup.

    Rules: lowercase, strip, collapse spaces.
    """
    return " ".join(name.lower().strip().split())


async def get_cached_product(normalized_name: str) -> Optional[dict]:
    """
    Check the products table for a cached entry.

    Returns product row as dict if found AND last_scraped_at is within 7 days.
    None if not found or expired.
    """
    try:
        sb = get_supabase()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        response = (
            sb.table("products")
            .select("*")
            .eq("normalized_name", normalized_name)
            .gt("last_scraped_at", cutoff.isoformat())
            .maybe_single()
            .execute()
        )
        # maybe_single().execute() returns None when no rows match in supabase-py v2
        if response is not None and response.data:
            return dict(response.data)
        return None
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", operation="get_cached_product", error=str(e), error_code=code)
        return None


async def store_product(product_data: dict) -> str:
    """
    Upsert a product into the cache by normalized_name.
    Returns the product id.
    """
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        data = {**product_data, "last_scraped_at": now}
        response = (
            sb.table("products")
            .upsert(data, on_conflict="normalized_name")
            .execute()
        )
        if response.data:
            row = response.data[0] if isinstance(response.data, list) else response.data
            return str(row["id"])
        return ""
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", operation="store_product", error=str(e), error_code=code)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Alternatives Cache
# ─────────────────────────────────────────────────────────────────────────────


async def get_cached_alternatives(normalized_name: str) -> Optional[list[dict]]:
    """
    Check the alternatives_cache table for a cached entry.

    Returns alternatives list if found AND scraped_at is within 30 days.
    None if not found or expired.
    """
    try:
        sb = get_supabase()
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        response = (
            sb.table("alternatives_cache")
            .select("alternatives")
            .eq("normalized_name", normalized_name)
            .gt("scraped_at", cutoff.isoformat())
            .maybe_single()
            .execute()
        )
        if response is not None and response.data and response.data.get("alternatives"):
            return response.data["alternatives"]
        return None
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", operation="get_cached_alternatives", error=str(e), error_code=code)
        return None


async def store_alternatives(
    product_name: str,
    alternatives: list[dict],
    source_url: str = "",
) -> str:
    """
    Upsert alternatives into the alternatives_cache table by normalized_name.
    Returns the row id.
    """
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "product_name": product_name,
            "normalized_name": normalize_product_name(product_name),
            "alternatives": alternatives,
            "source_url": source_url or None,
            "scraped_at": now,
        }
        response = (
            sb.table("alternatives_cache")
            .upsert(data, on_conflict="normalized_name")
            .execute()
        )
        if response.data:
            row = response.data[0] if isinstance(response.data, list) else response.data
            return str(row["id"])
        return ""
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", operation="store_alternatives", error=str(e), error_code=code)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Journeys
# ─────────────────────────────────────────────────────────────────────────────


async def create_journey(prompt: str, intent_type: str = "explore") -> str:
    """
    Create a new journey row.
    Sets title=first 100 chars of prompt, status=active, intent_type, initial_prompt.
    Returns the journey id.
    """
    try:
        sb = get_supabase()
        title = (prompt[:100] + "…") if len(prompt) > 100 else prompt
        data = {
            "title": title,
            "status": "active",
            "intent_type": intent_type,
            "initial_prompt": prompt,
        }
        response = sb.table("journeys").insert(data).execute()
        if response.data:
            row = response.data[0] if isinstance(response.data, list) else response.data
            return str(row["id"])
        return ""
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", operation="create_journey", error=str(e), error_code=code)
        return ""


async def get_journey(journey_id: str) -> Optional[dict]:
    """
    Get a journey with all its steps ordered by step_number.
    Returns dict with "steps" list, or None if not found.
    """
    try:
        sb = get_supabase()
        journey_response = (
            sb.table("journeys")
            .select("*")
            .eq("id", journey_id)
            .maybe_single()
            .execute()
        )
        if journey_response is None or not journey_response.data:
            return None

        journey = dict(journey_response.data)

        steps_response = (
            sb.table("journey_steps")
            .select("*")
            .eq("journey_id", journey_id)
            .order("step_number")
            .execute()
        )
        journey["steps"] = [dict(s) for s in (steps_response.data or [])]
        return journey
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", journey_id=journey_id, operation="get_journey", error=str(e), error_code=code)
        return None


async def list_journeys() -> list[dict]:
    """
    List all journeys ordered by updated_at desc.
    Includes step_count for each journey.
    """
    try:
        sb = get_supabase()
        journeys_response = (
            sb.table("journeys")
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
        journeys = journeys_response.data or []

        if not journeys:
            return []

        journey_ids = [str(j["id"]) for j in journeys]
        steps_response = sb.table("journey_steps").select("journey_id").execute()
        steps = steps_response.data or []

        step_counts: dict[str, int] = {}
        for s in steps:
            jid = str(s["journey_id"])
            step_counts[jid] = step_counts.get(jid, 0) + 1

        result = []
        for j in journeys:
            row = dict(j)
            row["step_count"] = step_counts.get(str(j["id"]), 0)
            result.append(row)

        return result
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", operation="list_journeys", error=str(e), error_code=code)
        return []


async def update_journey_status(journey_id: str, status: str) -> None:
    """Update journey status and updated_at."""
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        sb.table("journeys").update({"status": status, "updated_at": now}).eq("id", journey_id).execute()
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", journey_id=journey_id, operation="update_journey_status", error=str(e), error_code=code)


async def save_journey_step(
    journey_id: str,
    step_number: int,
    step_type: str,
    input_data: Any = None,
    output_data: Any = None,
    user_selection: Any = None,
) -> str:
    """
    Insert a new step into journey_steps.
    Returns the step id.
    """
    try:
        sb = get_supabase()
        data = {
            "journey_id": journey_id,
            "step_number": step_number,
            "step_type": step_type,
            "input_data": input_data,
            "output_data": output_data,
            "user_selection": user_selection,
        }
        response = sb.table("journey_steps").insert(data).execute()
        if response.data:
            row = response.data[0] if isinstance(response.data, list) else response.data
            return str(row["id"])
        return ""
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", journey_id=journey_id, operation="save_journey_step", error=str(e), error_code=code)
        return ""


async def get_last_step(journey_id: str) -> Optional[dict]:
    """
    Get the most recent step for a journey (highest step_number).
    """
    try:
        sb = get_supabase()
        response = (
            sb.table("journey_steps")
            .select("*")
            .eq("journey_id", journey_id)
            .order("step_number", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if response is not None and response.data:
            return dict(response.data)
        return None
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", journey_id=journey_id, operation="get_last_step", error=str(e), error_code=code)
        return None


async def get_next_step_number(journey_id: str) -> int:
    """
    Get the next step_number for a journey.
    Returns max(step_number) + 1, or 1 if no steps exist.
    """
    try:
        sb = get_supabase()
        response = (
            sb.table("journey_steps")
            .select("step_number")
            .eq("journey_id", journey_id)
            .order("step_number", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if response is not None and response.data:
            return int(response.data["step_number"]) + 1
        return 1
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", journey_id=journey_id, operation="get_next_step_number", error=str(e), error_code=code)
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# LLM State
# ─────────────────────────────────────────────────────────────────────────────


async def get_llm_state() -> str:
    """
    Get the active LLM provider from llm_state table.
    If no row exists, returns first provider in LLM_CONFIG fallback_chain.
    """
    try:
        sb = get_supabase()
        response = (
            sb.table("llm_state")
            .select("active_provider")
            .eq("id", 1)
            .maybe_single()
            .execute()
        )
        if response is not None and response.data and response.data.get("active_provider"):
            return response.data["active_provider"]
        return LLM_CONFIG["fallback_chain"][0]
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", operation="get_llm_state", error=str(e), error_code=code)
        return LLM_CONFIG["fallback_chain"][0]


async def update_llm_state(provider: str, reason: str) -> None:
    """
    Upsert on id=1 in llm_state table.
    Sets active_provider, switched_at, switch_reason, updated_at.
    """
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": 1,
            "active_provider": provider,
            "switched_at": now,
            "switch_reason": reason,
            "updated_at": now,
        }
        sb.table("llm_state").upsert(data, on_conflict="id").execute()
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", operation="update_llm_state", error=str(e), error_code=code)


# ─────────────────────────────────────────────────────────────────────────────
# Figma OAuth Tokens
# ─────────────────────────────────────────────────────────────────────────────


def store_figma_tokens(
    session_id: str,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> None:
    """
    Upsert Figma tokens for a session.
    Used after OAuth callback token exchange.
    """
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "session_id": session_id,
            "access_token": access_token,
            "refresh_token": refresh_token or None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": now,
        }
        sb.table("figma_tokens").upsert(data, on_conflict="session_id").execute()
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db write failed", operation="store_figma_tokens", error=str(e), error_code=code)


def get_figma_tokens(session_id: str) -> Optional[dict]:
    """
    Get Figma tokens for a session.
    Returns None if not found or expired (expires_at in past).
    """
    try:
        sb = get_supabase()
        response = (
            sb.table("figma_tokens")
            .select("*")
            .eq("session_id", session_id)
            .maybe_single()
            .execute()
        )
        if response is None or not response.data:
            return None
        row = dict(response.data)
        expires_at = row.get("expires_at")
        if expires_at:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if isinstance(expires_at, str) else expires_at
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= exp_dt:
                return None
        return row
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "db read failed", operation="get_figma_tokens", error=str(e), error_code=code)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# User Choice Logging (fire-and-forget)
# ─────────────────────────────────────────────────────────────────────────────


async def log_user_choice(
    journey_id: str,
    step_id: str,
    options_presented: dict | list,
    options_selected: dict | list,
) -> None:
    """
    Insert into user_choices_log. Fire-and-forget — log errors, don't raise.
    """
    try:
        sb = get_supabase()
        sb.table("user_choices_log").insert(
            {
                "journey_id": journey_id,
                "step_id": step_id,
                "options_presented": options_presented,
                "options_selected": options_selected,
            }
        ).execute()
    except Exception as e:
        log("WARN", "user_choices_log insert failed", journey_id=journey_id, step_id=step_id, error=str(e))
