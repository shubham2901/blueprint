"""
Blueprint Backend — Code Generation API

POST /api/code/generate: design context → transform → vision LLM → validate JSX → store.
GET /api/code/session: return current prototype session for bp_session cookie.
"""

import base64
import time
import uuid

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request, Response

from app.config import generate_error_code, log, settings
from app.db import (
    create_prototype_session,
    get_figma_tokens,
    get_prototype_session,
    update_prototype_session,
)
from app.figma_context import transform_design_context
from app.llm import LLMError, call_llm_vision, strip_code_fences
from app.models import CodeGenerateRequest, CodeGenerateResponse
from app.prompts import build_design_to_code_prompt

router = APIRouter(prefix="/api/code", tags=["code"])
SESSION_COOKIE = "bp_session"


def _is_secure() -> bool:
    return settings.environment == "production"


def _cookie_samesite() -> str:
    """Return 'none' for production (cross-origin), 'lax' for local dev (same-origin)."""
    return "none" if settings.environment == "production" else "lax"


def _get_session_and_tokens(request: Request, bp_session: str | None) -> tuple[str, dict | None]:
    """
    Get session_id and Figma tokens for the request.
    Returns (session_id, tokens). tokens is None if not connected.
    """
    from app.auth import get_current_user_id

    user_id = get_current_user_id(request)
    if user_id:
        tokens = get_figma_tokens(user_id=user_id)
        session_id = bp_session or user_id or str(uuid.uuid4())
    else:
        tokens = get_figma_tokens(session_id=bp_session) if bp_session else None
        session_id = bp_session or str(uuid.uuid4())
    return session_id, tokens


def _validate_jsx(code: str) -> tuple[bool, str | None]:
    """Validate JSX by transforming with esbuild. Return (valid, error_message)."""
    try:
        from esbuild_py import transform

        transform(code)
        return True, None
    except Exception as e:
        return False, str(e)


def _count_icons(tree: list[dict]) -> int:
    """Count VECTOR/BOOLEAN_OPERATION nodes (icons) in the tree."""
    count = 0
    for node in tree:
        if isinstance(node, dict):
            if node.get("type") in ("VECTOR", "BOOLEAN_OPERATION"):
                count += 1
            count += _count_icons(node.get("children", []))
    return count


@router.post("/generate", response_model=CodeGenerateResponse)
async def code_generate(
    body: CodeGenerateRequest,
    request: Request,
    response: Response,
    bp_session: str | None = Cookie(default=None),
) -> CodeGenerateResponse:
    """
    POST /api/code/generate

    Transform design context, call vision LLM, validate JSX, store in prototype_sessions.
    Requires Figma tokens (OAuth). Auto-retry once on validation failure.
    """
    session_id, tokens = _get_session_and_tokens(request, bp_session)
    if not tokens:
        code = generate_error_code()
        log("ERROR", "code generation no tokens", session_id=session_id[:8] if session_id else "none", error_code=code)
        raise HTTPException(
            status_code=401,
            detail={"message": "Connect with Figma to generate code.", "error_code": code},
        )

    # Ensure session cookie is set for anonymous users
    if not bp_session and session_id:
        response.set_cookie(
            key=SESSION_COOKIE,
            value=session_id,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            secure=_is_secure(),
            samesite=_cookie_samesite(),
            path="/",
        )

    start_ms = time.perf_counter()
    log(
        "INFO",
        "code generation started",
        session_id=session_id[:8],
        frame_name=body.frame_name,
        has_thumbnail=bool(body.thumbnail_url),
    )

    # 1. Create session with status=generating
    await create_prototype_session(
        session_id=session_id,
        design_context=body.design_context,
        thumbnail_url=body.thumbnail_url,
        frame_name=body.frame_name,
        frame_width=body.frame_width,
        frame_height=body.frame_height,
        status="generating",
    )

    # 2. Transform design context
    transformed = transform_design_context(body.design_context)
    tree = transformed.get("tree", [])
    icon_count = _count_icons(tree)
    log("INFO", "design context transformed", session_id=session_id[:8], tree_nodes=len(tree), icon_count=icon_count)

    # 3. Fetch thumbnail → base64
    image_base64: str | None = None
    if body.thumbnail_url:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(body.thumbnail_url)
            if r.status_code == 200:
                image_base64 = base64.b64encode(r.content).decode()
                log("INFO", "thumbnail fetched for vision", session_id=session_id[:8], image_size_bytes=len(r.content))
            else:
                log("WARN", "thumbnail fetch failed", session_id=session_id[:8], error=f"HTTP {r.status_code}")
        except Exception as e:
            log("WARN", "thumbnail fetch failed", session_id=session_id[:8], error=str(e))

    # 4. Icon handling — skip SVG fetching, use placeholders (saves ~100K+ tokens)
    log("INFO", "using placeholder icons", session_id=session_id[:8], icon_count=icon_count)

    # 5. Build prompt, call vision LLM
    prompt_text = build_design_to_code_prompt(transformed)
    messages = [{"role": "user", "content": prompt_text}]

    try:
        raw_code = await call_llm_vision(messages, image_base64, session_id=session_id)
    except LLMError as e:
        code = generate_error_code()
        reason = "frame_too_large" if e.context_window_exceeded else None
        log("ERROR", "code generation failed", session_id=session_id[:8], error_code=code, error=str(e), error_reason=reason)
        await update_prototype_session(session_id=session_id, status="error", error_code=code)
        return CodeGenerateResponse(session_id=session_id, status="error", error_code=code, error_reason=reason)

    code_str = strip_code_fences(raw_code)

    # 6. Validate JSX
    valid, err_msg = _validate_jsx(code_str)
    if not valid:
        log("WARN", "jsx validation failed", session_id=session_id[:8], error=(err_msg or "")[:200])
        # Retry once
        log("WARN", "code generation retry", session_id=session_id[:8], attempt=2, reason="jsx validation failed")
        try:
            raw_code = await call_llm_vision(messages, image_base64, session_id=session_id)
            code_str = strip_code_fences(raw_code)
            valid, err_msg = _validate_jsx(code_str)
        except LLMError as retry_e:
            code = generate_error_code()
            log("ERROR", "code generation failed", session_id=session_id[:8], error_code=code, error=str(retry_e))
            await update_prototype_session(session_id=session_id, status="error", error_code=code)
            return CodeGenerateResponse(session_id=session_id, status="error", error_code=code)

        if not valid:
            code = generate_error_code()
            log("ERROR", "code generation failed", session_id=session_id[:8], error_code=code, error=(err_msg or "")[:200])
            ok = await update_prototype_session(session_id=session_id, status="error", error_code=code)
            if not ok:
                log("ERROR", "db write failed", session_id=session_id[:8], operation="update_prototype_session", error_code=code)
            return CodeGenerateResponse(session_id=session_id, status="error", error_code=code)

    log("INFO", "jsx validation passed", session_id=session_id[:8], code_length=len(code_str))

    # 7. Store success
    ok = await update_prototype_session(
        session_id=session_id,
        generated_code=code_str,
        status="ready",
    )
    if not ok:
        code = generate_error_code()
        log("ERROR", "db write failed", session_id=session_id[:8], operation="update_prototype_session", error="update failed", error_code=code)
        await update_prototype_session(session_id=session_id, status="error", error_code=code)
        return CodeGenerateResponse(session_id=session_id, status="error", error_code=code)

    duration_ms = int((time.perf_counter() - start_ms) * 1000)
    log("INFO", "code generation completed", session_id=session_id[:8], duration_ms=duration_ms, code_length=len(code_str))

    return CodeGenerateResponse(session_id=session_id, status="ready")


@router.get("/session")
async def get_session(
    bp_session: str | None = Cookie(default=None),
) -> dict:
    """
    GET /api/code/session

    Returns current PrototypeSession for bp_session cookie, or 404 if none.
    """
    session_id = bp_session
    if not session_id:
        raise HTTPException(status_code=404, detail="No session")

    session = await get_prototype_session(session_id)
    if not session:
        log("INFO", "session not found", session_id=session_id[:8])
        raise HTTPException(status_code=404, detail="No prototype session found")

    log("INFO", "session retrieved", session_id=session_id[:8], status=session.get("status"))
    return session
