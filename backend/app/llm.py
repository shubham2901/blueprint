"""
Blueprint Backend — LLM Interactions

All LLM calls via litellm: completion, structured output validation,
fallback chain, provider state caching.
"""

import json
import re
import time
import warnings

import litellm
from pydantic import BaseModel, ValidationError

from app import db
from app.config import CODE_GEN_MODEL, LLM_CONFIG, generate_error_code, log

# ── Suppress noisy litellm warnings ──────────────────────────────────────────
# litellm internally creates VertexLLM coroutines that sometimes go un-awaited
# when the gemini/ prefix routes through a code path that raises before awaiting.
warnings.filterwarnings(
    "ignore",
    message="coroutine 'VertexLLM.async_completion' was never awaited",
)
litellm.suppress_debug_info = True
litellm.drop_params = True  # Prevent unsupported-param errors across providers

# Module-level state
_active_provider: str | None = None
_initialized: bool = False

# ── Rate-limit cooldown cache ────────────────────────────────────────────────
# Maps provider name → timestamp (time.monotonic) when the rate-limit was hit.
# Providers in this dict are skipped until RATE_LIMIT_COOLDOWN_SECONDS elapse.
_rate_limited_until: dict[str, float] = {}
RATE_LIMIT_COOLDOWN_SECONDS = 600  # Skip rate-limited provider for 10 minutes (daily quota)
LLM_CALL_TIMEOUT_SECONDS = 90     # Per-provider timeout — increased for vision/large requests


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate-limit / quota error (transient)."""
    error_str = str(error).lower()
    return any(kw in error_str for kw in (
        "rate_limit", "ratelimit", "429", "quota", "resource_exhausted",
        "timeout", "timed out",
    ))


def _mark_rate_limited(provider: str) -> None:
    """Record that a provider just hit a rate limit."""
    _rate_limited_until[provider] = time.monotonic() + RATE_LIMIT_COOLDOWN_SECONDS
    log("WARN", "provider rate-limited, will skip for cooldown",
        provider=provider, cooldown_seconds=RATE_LIMIT_COOLDOWN_SECONDS)


def _is_in_cooldown(provider: str) -> bool:
    """Return True if the provider is still in rate-limit cooldown."""
    deadline = _rate_limited_until.get(provider)
    if deadline is None:
        return False
    if time.monotonic() >= deadline:
        # Cooldown expired — allow retry
        del _rate_limited_until[provider]
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────────────────────────────────────


class LLMError(Exception):
    """All providers in the fallback chain failed."""

    pass


class LLMValidationError(Exception):
    """LLM output failed Pydantic validation even after retry."""

    def __init__(self, raw_output: str, expected_schema: str, error: str):
        self.raw_output = raw_output
        self.expected_schema = expected_schema
        super().__init__(f"LLM validation failed: {error}")


# ─────────────────────────────────────────────────────────────────────────────
# Core Functions
# ─────────────────────────────────────────────────────────────────────────────


async def call_llm(messages: list[dict], journey_id: str | None = None) -> str:
    """
    Call the LLM with automatic per-request fallback through the entire chain.

    For every request we walk the full fallback chain starting from position 0.
    Rate-limit errors are treated as transient — we skip the model for this
    request but don't persist the switch.  Non-transient failures (auth errors,
    model not found, etc.) persist the switch via DB so subsequent requests
    start from the new provider.

    Args:
        messages: List of message dicts (without system prompt — injected here).
        journey_id: Optional journey ID for logging correlation.

    Returns:
        Raw response content string from the LLM.

    Raises:
        LLMError: If all providers in the fallback chain fail.
    """
    await _ensure_initialized()
    full_messages = _inject_system_prompt(messages)
    chain = LLM_CONFIG["fallback_chain"]
    last_error: Exception | None = None
    tried_any = False

    for idx, provider in enumerate(chain):
        # ── Skip providers that are still in rate-limit cooldown ──
        if _is_in_cooldown(provider):
            log(
                "INFO",
                "skipping rate-limited provider",
                journey_id=journey_id,
                provider=provider,
            )
            continue

        tried_any = True
        log(
            "INFO",
            "llm call started",
            journey_id=journey_id,
            provider=provider,
            prompt_type="completion",
        )
        start = time.perf_counter()

        try:
            # Build completion kwargs
            completion_kwargs = {
                "model": provider,
                "messages": full_messages,
                "temperature": LLM_CONFIG["temperature"],
                "max_tokens": LLM_CONFIG["max_tokens"],
                "timeout": LLM_CALL_TIMEOUT_SECONDS,
            }
            # Gemini 2.5 models may need explicit JSON mode to avoid empty content
            # when the model uses "thinking" internally
            if "gemini-2.5" in provider:
                completion_kwargs["response_format"] = {"type": "json_object"}
            
            response = await litellm.acompletion(**completion_kwargs)
            duration_ms = int((time.perf_counter() - start) * 1000)
            
            # Extract content with detailed fallback handling
            content = ""
            if response.choices:
                msg = response.choices[0].message
                # Try standard content field first
                if msg.content:
                    content = msg.content
                # Gemini 2.5 "thinking" models may return reasoning separately
                elif hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                    # If only reasoning exists (no content), use it as a fallback
                    content = msg.reasoning_content

            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "total_tokens", None)

            # If we got tokens but no content, treat it as an error and fallback
            # This handles Gemini 2.5 "thinking" mode returning empty content
            if not content:
                log(
                    "WARN",
                    "llm returned empty content, will try next provider",
                    journey_id=journey_id,
                    provider=provider,
                    duration_ms=duration_ms,
                    tokens_used=tokens_used,
                )
                raise ValueError(f"Provider {provider} returned empty content")

            log(
                "INFO",
                "llm call succeeded",
                journey_id=journey_id,
                provider=provider,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
            )

            # If we fell back to a different provider due to a non-transient error,
            # persist the switch so future requests start here.
            if provider != chain[0] and last_error and not _is_rate_limit_error(last_error):
                global _active_provider
                _active_provider = provider
                await db.update_llm_state(provider, reason=f"Fallback after: {last_error!s}")

            return content

        except Exception as e:
            code = generate_error_code()
            log(
                "ERROR",
                "llm call failed",
                journey_id=journey_id,
                provider=provider,
                error=str(e),
                error_code=code,
            )
            last_error = e

            # Mark as rate-limited so future requests skip it immediately
            if _is_rate_limit_error(e):
                _mark_rate_limited(provider)

            # Log the fallback attempt — find the next non-cooldown provider
            next_provider = None
            for nxt in chain[idx + 1:]:
                if not _is_in_cooldown(nxt):
                    next_provider = nxt
                    break
            if next_provider:
                log(
                    "WARN",
                    "llm provider fallback",
                    journey_id=journey_id,
                    from_provider=provider,
                    to_provider=next_provider,
                    reason=str(e),
                )
            continue

    # If every provider was in cooldown and we never tried any, clear the
    # cooldowns and retry the first provider as a last-ditch attempt.
    if not tried_any:
        log("WARN", "all providers in cooldown, clearing cooldowns for retry",
            journey_id=journey_id)
        _rate_limited_until.clear()
        return await call_llm(messages, journey_id=journey_id)

    raise LLMError("All LLM providers failed")


async def call_llm_structured(
    messages: list[dict],
    response_model: type[BaseModel],
    journey_id: str | None = None,
) -> BaseModel:
    """
    Call LLM and validate the response against a Pydantic model.

    Steps:
        1. Call call_llm(messages) to get raw response
        2. Strip markdown code fences if present (```json ... ```)
        3. json.loads() the response
        4. Validate with response_model(**parsed_json)
        5. On JSONDecodeError or ValidationError:
           a. Build a "fix JSON" prompt with the broken output + expected schema
           b. Retry call_llm() once with the fix prompt
           c. Parse and validate the retry response
           d. If retry also fails: raise LLMValidationError
        6. Return the validated Pydantic model instance

    Args:
        messages: Chat messages (without system prompt).
        response_model: The Pydantic model class to validate against.
        journey_id: Optional journey ID for logging correlation.

    Returns:
        An instance of response_model.

    Raises:
        LLMValidationError: If validation fails after retry.
    """
    from app.prompts import build_fix_json_prompt

    raw = await call_llm(messages, journey_id=journey_id)
    stripped = _strip_code_fences(raw)

    try:
        parsed = json.loads(stripped)
        return response_model.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        error_code = generate_error_code()
        # Log with actual validation error for debugging
        log(
            "ERROR",
            "llm output validation failed",
            journey_id=journey_id,
            raw_output=raw[:500] + "..." if len(raw) > 500 else raw,
            schema=response_model.__name__,
            validation_error=str(e)[:300],
            error_code=error_code,
        )

        # Retry with fix prompt that includes original context for better regeneration.
        # Append the fix instructions to the original messages so the LLM has full context.
        fix_instruction = (
            f"\n\n---\n\n"
            f"Your previous response had a JSON error. Here is what you returned:\n\n"
            f"```\n{raw}\n```\n\n"
            f"The error was: {str(e)}\n\n"
            f"Please output ONLY valid JSON matching this schema (no markdown, no explanation):\n"
            f"{json.dumps(response_model.model_json_schema(), indent=2)}"
        )
        # Clone original messages and append fix instruction to the last user message
        retry_messages = [dict(m) for m in messages]
        if retry_messages and retry_messages[-1].get("role") == "user":
            retry_messages[-1]["content"] += fix_instruction
        else:
            retry_messages.append({"role": "user", "content": fix_instruction})
        
        retry_raw = await call_llm(retry_messages, journey_id=journey_id)
        retry_stripped = _strip_code_fences(retry_raw)

        try:
            retry_parsed = json.loads(retry_stripped)
            return response_model.model_validate(retry_parsed)
        except (json.JSONDecodeError, ValidationError) as retry_e:
            raise LLMValidationError(
                raw_output=retry_raw,
                expected_schema=json.dumps(response_model.model_json_schema(), indent=2),
                error=str(retry_e),
            )


# Vision-capable models fallback chain (design-to-code)
VISION_FALLBACK_CHAIN = [
    "gemini/gemini-2.5-pro",      # Primary — best quality
    "gemini/gemini-3-pro",        # Fallback 1 — Gemini 3
    "openai/gpt-4o",              # Fallback 2 — OpenAI vision
]


async def call_llm_vision(
    messages: list[dict],
    image_base64: str | None,
    session_id: str | None = None,
) -> str:
    """
    Call the vision-capable LLM for design-to-code generation.

    Accepts base64-encoded image (caller fetches thumbnail and encodes).
    Prepends image to the first user message as multimodal content.
    Uses VISION_FALLBACK_CHAIN with automatic fallback on failure.
    No response_format (Gemini JSON mode conflicts with vision; code output is plain text).

    Args:
        messages: Chat messages (system + user; no injection here).
        image_base64: Base64-encoded PNG, or None for text-only.
        session_id: Optional session ID for logging correlation.

    Returns:
        Raw response content string from the LLM.

    Raises:
        LLMError: If all vision providers fail.
    """
    # Build messages with optional image prepended to first user message
    final_messages = [dict(m) for m in messages]
    if image_base64:
        for i, msg in enumerate(final_messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                else:
                    content = list(content)
                content.insert(
                    0,
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                )
                final_messages[i] = {**msg, "content": content}
                break

    last_error: Exception | None = None

    for idx, provider in enumerate(VISION_FALLBACK_CHAIN):
        # Skip providers in cooldown
        if _is_in_cooldown(provider):
            log(
                "INFO",
                "skipping rate-limited vision provider",
                session_id=session_id,
                provider=provider,
            )
            continue

        log(
            "INFO",
            "llm vision call started",
            session_id=session_id,
            provider=provider,
            prompt_type="design_to_code",
            has_image=bool(image_base64),
        )
        start = time.perf_counter()

        try:
            response = await litellm.acompletion(
                model=provider,
                messages=final_messages,
                temperature=0.3,
                max_tokens=8000,
                timeout=LLM_CALL_TIMEOUT_SECONDS,
            )
            duration_ms = int((time.perf_counter() - start) * 1000)

            content = ""
            if response.choices:
                msg = response.choices[0].message
                if msg.content:
                    content = msg.content
                elif hasattr(msg, "reasoning_content") and msg.reasoning_content:
                    content = msg.reasoning_content

            if not content:
                log(
                    "WARN",
                    "llm vision returned empty content, trying next provider",
                    session_id=session_id,
                    provider=provider,
                )
                raise ValueError(f"Provider {provider} returned empty content")

            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "total_tokens", None)

            log(
                "INFO",
                "llm vision call succeeded",
                session_id=session_id,
                provider=provider,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                output_length=len(content),
            )
            return content

        except Exception as e:
            code = generate_error_code()
            log(
                "ERROR",
                "llm vision call failed",
                session_id=session_id,
                provider=provider,
                error=str(e),
                error_code=code,
            )
            last_error = e

            # Mark as rate-limited if applicable
            if _is_rate_limit_error(e):
                _mark_rate_limited(provider)

            # Log fallback attempt
            next_provider = None
            for nxt in VISION_FALLBACK_CHAIN[idx + 1:]:
                if not _is_in_cooldown(nxt):
                    next_provider = nxt
                    break
            if next_provider:
                log(
                    "WARN",
                    "llm vision provider fallback",
                    session_id=session_id,
                    from_provider=provider,
                    to_provider=next_provider,
                    reason=str(e),
                )
            continue

    raise LLMError(f"All vision providers failed. Last error: {last_error}") from last_error


# ─────────────────────────────────────────────────────────────────────────────
# Initialization & Fallback
# ─────────────────────────────────────────────────────────────────────────────


async def _ensure_initialized() -> None:
    """
    Load the active provider from the DB on first call.
    Sets _active_provider and _initialized.
    Called automatically by call_llm().
    """
    global _active_provider, _initialized
    if not _initialized:
        _active_provider = await db.get_llm_state()
        _initialized = True


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


def _inject_system_prompt(messages: list[dict]) -> list[dict]:
    """
    Prepend the persona system prompt to the message list.
    Returns a new list (does not mutate the input).
    """
    system_msg = {
        "role": "system",
        "content": LLM_CONFIG["persona"]["system_prompt"],
    }
    return [system_msg] + list(messages)


def _strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences from LLM output.
    Handles: ```json\n...\n```, ```\n...\n```, and plain text.
    """
    if not text or not isinstance(text, str):
        return text
    stripped = text.strip()
    # Match ```json\n...\n``` or ```\n...\n```
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def strip_code_fences(text: str) -> str:
    """
    Extract JSX/TSX/JavaScript from markdown code fences.

    Used when LLM returns markdown-wrapped code (e.g. ```jsx\n...\n```).
    Returns the first match or the original text if no fence found.

    Args:
        text: Raw LLM output that may contain code fences.

    Returns:
        Extracted code content or original text.
    """
    if not text or not isinstance(text, str):
        return text
    match = re.search(
        r"```(?:jsx|tsx|javascript)?\s*\n(.*?)```",
        text.strip(),
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return text.strip()
