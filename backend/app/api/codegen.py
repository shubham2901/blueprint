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

from app.config import generate_error_code, log
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
FIGMA_API_BASE = "https://api.figma.com/v1"


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


def _collect_icon_node_ids(tree: list[dict]) -> list[str]:
    """Recursively collect node IDs where type is VECTOR or BOOLEAN_OPERATION."""
    ids: list[str] = []

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            if isinstance(node, dict) and node.get("type") in ("VECTOR", "BOOLEAN_OPERATION"):
                nid = node.get("id")
                if nid:
                    ids.append(nid)
            children = node.get("children", []) if isinstance(node, dict) else []
            if children:
                walk(children)

    walk(tree)
    return ids


async def _fetch_icon_svgs(
    file_key: str,
    node_ids: list[str],
    access_token: str,
    session_id: str,
) -> dict[str, str]:
    """
    Fetch SVG content for icon nodes from Figma API.
    Returns dict mapping node_id -> svg_content.
    """
    if not file_key or not node_ids:
        return {}
    ids_param = ",".join(node_ids)
    url = f"{FIGMA_API_BASE}/images/{file_key}"
    params = {"ids": ids_param, "format": "svg"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            log("WARN", "icon svg export failed", session_id=session_id, error=f"HTTP {resp.status_code}")
            return {}
        data = resp.json()
        images = data.get("images", {}) or {}
        result: dict[str, str] = {}
        for nid, svg_url in images.items():
            if not svg_url:
                continue
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(svg_url)
                if r.status_code == 200 and r.text:
                    result[nid] = r.text
            except Exception as e:
                log("WARN", "icon svg fetch failed", session_id=session_id, node_id=nid, error=str(e))
        log("INFO", "icon svg export completed", session_id=session_id, icon_count=len(node_ids), fetched=len(result))
        return result
    except Exception as e:
        log("WARN", "icon svg export failed", session_id=session_id, error=str(e))
        return {}


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
            samesite="lax",
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
    icon_count = sum(1 for n in _flatten_tree(tree) if n.get("type") in ("VECTOR", "BOOLEAN_OPERATION"))
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

    # 4. Fetch icon SVGs (Task 4)
    access_token = tokens.get("access_token", "")
    icon_ids = _collect_icon_node_ids(tree)
    icons: dict[str, str] = {}
    if body.file_key and icon_ids and access_token:
        icons = await _fetch_icon_svgs(body.file_key, icon_ids, access_token, session_id)
    if icons:
        transformed["icons"] = icons

    # 5. Build prompt, call vision LLM
    prompt_text = build_design_to_code_prompt(transformed)
    messages = [{"role": "user", "content": prompt_text}]

    try:
        raw_code = await call_llm_vision(messages, image_base64, session_id=session_id)
    except LLMError as e:
        code = generate_error_code()
        log("ERROR", "code generation failed", session_id=session_id[:8], error_code=code, error=str(e))
        await update_prototype_session(session_id=session_id, status="error", error_code=code)
        return CodeGenerateResponse(session_id=session_id, status="error", error_code=code)

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


def _flatten_tree(tree: list[dict]) -> list[dict]:
    """Flatten tree for iteration."""
    out: list[dict] = []

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            if isinstance(node, dict):
                out.append(node)
                walk(node.get("children", []))

    walk(tree)
    return out


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
