"""
Blueprint Backend — Figma OAuth & Import API

OAuth 2 flow: start → Figma consent → callback (token exchange) → redirect to frontend.
Import: POST with Figma frame URL → fetch nodes → return design context.
"""

import base64
import re
import secrets
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.auth import get_current_user_id
from app.config import generate_error_code, log, settings
from app.db import (
    delete_figma_tokens,
    get_cached_figma_design,
    get_figma_tokens,
    store_figma_design_cache,
    store_figma_tokens,
)
from app.models import FigmaImportRequest, FigmaImportResponse

router = APIRouter(prefix="/api/figma", tags=["figma"])

FIGMA_AUTH_URL = "https://www.figma.com/oauth"
FIGMA_TOKEN_URL = "https://api.figma.com/v1/oauth/token"
SCOPES = "file_content:read,file_metadata:read"
STATE_COOKIE = "bp_figma_state"
SESSION_COOKIE = "bp_session"
STATE_MAX_AGE = 300  # 5 minutes
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


async def _refresh_figma_token(tokens: dict, *, user_id: str | None = None, session_id: str | None = None) -> dict | None:
    """
    Use refresh_token to get a new access_token from Figma.
    Returns updated token dict on success, None on failure.
    Figma refresh tokens are single-use — each refresh returns a new refresh_token.
    """
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        log("WARN", "figma token refresh skipped, no refresh_token")
        if user_id:
            delete_figma_tokens(user_id=user_id)
        elif session_id:
            delete_figma_tokens(session_id=session_id)
        return None

    try:
        basic_auth = base64.b64encode(
            f"{settings.figma_client_id}:{settings.figma_client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                FIGMA_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
    except Exception as e:
        log("ERROR", "figma token refresh request failed", error=str(e))
        return None

    if resp.status_code != 200:
        log("ERROR", "figma token refresh failed", status=resp.status_code, body=resp.text[:200])
        # Refresh token is dead — delete stale tokens so status returns "connected: false"
        if user_id:
            delete_figma_tokens(user_id=user_id)
        elif session_id:
            delete_figma_tokens(session_id=session_id)
        return None

    try:
        data = resp.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        expires_in = data.get("expires_in")
        if not new_access:
            log("ERROR", "figma token refresh returned no access_token")
            return None
    except Exception as e:
        log("ERROR", "figma token refresh parse failed", error=str(e))
        return None

    from datetime import datetime, timedelta, timezone
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    store_figma_tokens(new_access, new_refresh, expires_at, user_id=user_id, session_id=session_id)
    log("INFO", "figma token refreshed successfully")
    return {"access_token": new_access, "refresh_token": new_refresh, "expires_at": str(expires_at) if expires_at else None}


def _is_secure() -> bool:
    return settings.environment == "production"


def _cookie_samesite() -> str:
    """Return 'none' for production (cross-origin), 'lax' for local dev (same-origin)."""
    return "none" if settings.environment == "production" else "lax"


@router.get("/oauth/start")
async def oauth_start(response: Response) -> RedirectResponse:
    """
    GET /api/figma/oauth/start

    Generates state, stores in cookie, redirects to Figma OAuth consent.
    """
    if not settings.figma_client_id:
        log("ERROR", "figma oauth start failed", error="FIGMA_CLIENT_ID not configured", error_code="BP-CONFIG")
        redirect_url = f"{settings.frontend_url}?figma_error=1&error_code=BP-CONFIG"
        resp = RedirectResponse(url=redirect_url, status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.figma_client_id,
        "redirect_uri": settings.figma_redirect_uri,
        "scope": SCOPES,
        "state": state,
        "response_type": "code",
    }
    auth_url = f"{FIGMA_AUTH_URL}?{urlencode(params)}"

    resp = RedirectResponse(url=auth_url, status_code=302)
    resp.set_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=STATE_MAX_AGE,
        httponly=True,
        secure=_is_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    log("INFO", "figma oauth start", redirect_to="figma")
    return resp


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    bp_figma_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    """
    GET /api/figma/oauth/callback

    Validates state, exchanges code for tokens, stores tokens, sets session cookie,
    redirects to frontend with ?figma_connected=1 or ?figma_error=1&error_code=...
    """
    frontend_url = settings.frontend_url.rstrip("/")

    def _error_redirect(code_err: str) -> RedirectResponse:
        """Build error redirect, cleaning up all OAuth cookies."""
        resp = RedirectResponse(
            url=f"{frontend_url}?figma_error=1&error_code={code_err}",
            status_code=302,
        )
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

    # User denied or error from Figma
    if error:
        code_err = generate_error_code()
        log("ERROR", "figma oauth callback error", error=error, error_code=code_err)
        return _error_redirect(code_err)

    # Validate state (CSRF)
    if not state or not bp_figma_state or state != bp_figma_state:
        code_err = generate_error_code()
        log("ERROR", "figma oauth state mismatch", error_code=code_err)
        return _error_redirect(code_err)

    if not code:
        code_err = generate_error_code()
        log("ERROR", "figma oauth callback missing code", error_code=code_err)
        return _error_redirect(code_err)

    # Exchange code for tokens — MUST complete within 30 seconds
    try:
        basic_auth = base64.b64encode(
            f"{settings.figma_client_id}:{settings.figma_client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                FIGMA_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "redirect_uri": settings.figma_redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
    except Exception as e:
        code_err = generate_error_code()
        log("ERROR", "figma token exchange failed", error=str(e), error_code=code_err)
        return _error_redirect(code_err)

    if token_resp.status_code != 200:
        code_err = generate_error_code()
        log("ERROR", "figma token exchange failed", status=token_resp.status_code, body=token_resp.text[:200], error_code=code_err)
        return _error_redirect(code_err)

    try:
        data = token_resp.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")  # seconds until expiry
        if not access_token:
            raise ValueError("No access_token in response")
    except Exception as e:
        code_err = generate_error_code()
        log("ERROR", "figma token response parse failed", error=str(e), error_code=code_err)
        return _error_redirect(code_err)

    # Store tokens: by user_id (logged in) or session_id (anonymous)
    from datetime import datetime, timedelta, timezone
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    user_id = get_current_user_id(request)
    if user_id:
        store_figma_tokens(access_token, refresh_token, expires_at, user_id=user_id)
        log("INFO", "figma oauth complete", user_id=user_id[:8])
    else:
        session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())
        store_figma_tokens(access_token, refresh_token, expires_at, session_id=session_id)
        log("INFO", "figma oauth complete", session_id=session_id[:8])

    resp = RedirectResponse(url=f"{frontend_url}?figma_connected=1", status_code=302)
    resp.delete_cookie(STATE_COOKIE, path="/")
    if not user_id:
        resp.set_cookie(
            key=SESSION_COOKIE,
            value=session_id,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=_is_secure(),
            samesite=_cookie_samesite(),
            path="/",
        )
    return resp


FIGMA_API_BASE = "https://api.figma.com/v1"
GENERIC_NAMES = {"Rectangle", "Frame", "Ellipse", "Line", "Vector", "Text", "Group"}


def parse_figma_url(url: str) -> tuple[str | None, str | None]:
    """
    Extract (file_key, node_id) from Figma design URL.
    node_id returned in API format (colon, not hyphen).
    Supports: figma.com/design/:key/:name?node-id=X-Y, figma.com/file/:key
    """
    from urllib.parse import urlparse, parse_qs

    url = url.strip()
    if "figma.com" not in url:
        return None, None
    try:
        parsed = urlparse(url)
        path = parsed.path
        # Path: /design/FILE_KEY/... or /file/FILE_KEY/...
        path_match = re.match(r"/(?:design|file)/([0-9a-zA-Z]{6,128})", path)
        if not path_match:
            return None, None
        file_key = path_match.group(1)
        # Node ID from query: node-id=X-Y
        query = parse_qs(parsed.query)
        node_id_raw = query.get("node-id", [None])[0]
        node_id = node_id_raw.replace("-", ":") if node_id_raw else None
        return file_key, node_id
    except Exception:
        return None, None


def _validate_design_context(data: dict) -> list[str]:
    """Run validation on design context. Never block — return warnings only."""
    warnings: list[str] = []
    nodes = data.get("nodes", {})
    components = data.get("components", {})
    # Check for components
    if not components:
        warnings.append("No components found")
    # Check for generic layer names in nodes
    has_generic = False
    for node_data in nodes.values():
        if isinstance(node_data, dict) and "document" in node_data:
            doc = node_data.get("document", {})
            name = doc.get("name", "")
            if name in GENERIC_NAMES:
                has_generic = True
                break
            # Check layoutMode for Auto Layout
            if doc.get("layoutMode") is None and doc.get("type") == "FRAME":
                pass  # Optional: "Auto Layout not detected"
    if has_generic:
        warnings.append("Some layers may have generic names")
    return warnings


def _get_figma_tokens_for_request(request: Request, bp_session: str | None) -> dict | None:
    """Get Figma tokens: by user_id if logged in, else by session_id from cookie."""
    user_id = get_current_user_id(request)
    if user_id:
        return get_figma_tokens(user_id=user_id)
    if bp_session:
        return get_figma_tokens(session_id=bp_session)
    return None


@router.post("/import", response_model=FigmaImportResponse)
async def figma_import(
    body: FigmaImportRequest,
    request: Request,
    bp_session: str | None = Cookie(default=None),
) -> FigmaImportResponse:
    """
    POST /api/figma/import

    Import a Figma frame by URL. Requires OAuth tokens (by user or session).
    Returns design context (nodes, components, styles) and optional warnings.
    """
    tokens = _get_figma_tokens_for_request(request, bp_session)
    if not tokens:
        code = generate_error_code()
        log("ERROR", "figma import no tokens", error_code=code)
        raise HTTPException(
            status_code=401,
            detail={"message": "Connect with Figma to import this frame.", "error_code": code},
        )

    # Parse URL
    file_key, node_id = parse_figma_url(body.url)
    if not file_key or not node_id:
        code = generate_error_code()
        log("ERROR", "figma import invalid url", url=body.url[:50], error_code=code)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "That doesn't look like a valid Figma frame URL. Check the link and try again.",
                "error_code": code,
            },
        )

    # Check DB cache first — reduces Figma API calls (survives restarts)
    cached = get_cached_figma_design(file_key, node_id)
    if cached:
        design_context = cached.get("design_context", {})
        thumbnail_url = cached.get("thumbnail_url")
        frame_name = cached.get("frame_name")
        frame_width = cached.get("frame_width")
        frame_height = cached.get("frame_height")
        child_count = cached.get("child_count", 0)
        warnings = _validate_design_context(design_context)
        log("INFO", "figma import cache hit (db)", file_key=file_key[:8])
        return FigmaImportResponse(
            design_context=design_context,
            warnings=warnings,
            thumbnail_url=thumbnail_url,
            frame_name=frame_name,
            frame_width=frame_width,
            frame_height=frame_height,
            child_count=child_count,
            file_key=file_key,
            node_id=node_id,
        )

    # Resolve identity for potential token refresh
    user_id = get_current_user_id(request)

    # Fetch from Figma API
    access_token = tokens.get("access_token", "")
    api_url = f"{FIGMA_API_BASE}/files/{file_key}/nodes"
    log("INFO", "figma import started", file_key=file_key[:8], node_id=node_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                api_url,
                params={"ids": node_id},
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "figma import fetch failed", error=str(e), error_code=code)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "We couldn't import that frame. It may be private or the link may have expired.",
                "error_code": code,
            },
        )

    if resp.status_code == 403:
        # Access token expired — attempt one refresh, then retry once
        log("WARN", "figma import 403, attempting token refresh")
        refreshed = await _refresh_figma_token(
            tokens,
            user_id=user_id if user_id else None,
            session_id=bp_session if not user_id else None,
        )
        if not refreshed:
            # Refresh failed (invalid_grant, no refresh_token, etc.)
            # Tokens already deleted by _refresh_figma_token — tell user to re-auth
            code = generate_error_code()
            log("ERROR", "figma import 403, refresh failed, re-auth required", error_code=code)
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Your Figma connection has expired. Please reconnect with Figma and try again.",
                    "error_code": code,
                },
            )

        # Refresh succeeded — retry the import once with new token
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    api_url,
                    params={"ids": node_id},
                    headers={"Authorization": f"Bearer {refreshed['access_token']}"},
                )
        except Exception as e:
            code = generate_error_code()
            log("ERROR", "figma import retry fetch failed", error=str(e), error_code=code)
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "We couldn't import that frame. Please try again.",
                    "error_code": code,
                },
            )
        if resp.status_code == 200:
            log("INFO", "figma import succeeded after token refresh")
        elif resp.status_code == 403:
            # Even fresh token got 403 — file is genuinely inaccessible
            code = generate_error_code()
            log("ERROR", "figma import 403 with fresh token, file inaccessible", error_code=code)
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "We couldn't access that frame. It may be private or you may not have permission.",
                    "error_code": code,
                },
            )
    if resp.status_code == 404:
        code = generate_error_code()
        log("ERROR", "figma import 404 not found", error_code=code)
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't import that frame. It may be private or the link may have expired.",
                "error_code": code,
            },
        )
    if resp.status_code == 429:
        retry_after_raw = resp.headers.get("Retry-After", "")
        upgrade_url = resp.headers.get("X-Figma-Upgrade-Link") or None
        plan_tier = resp.headers.get("X-Figma-Plan-Tier") or None
        rate_limit_type = resp.headers.get("X-Figma-Rate-Limit-Type") or None
        retry_after_seconds: int | None = None
        try:
            retry_after_seconds = int(retry_after_raw) if retry_after_raw else None
        except ValueError:
            pass
        code = generate_error_code()
        log(
            "ERROR",
            "figma import rate limited",
            error_code=code,
            retry_after=retry_after_raw,
            plan_tier=plan_tier,
            rate_limit_type=rate_limit_type,
            upgrade_url=upgrade_url,
            body=resp.text[:200],
        )

        # No auto-retry on 429 — surface error immediately to user
        # Retrying burns quota and makes the problem worse
        detail: dict = {
            "message": "Figma's API is rate limiting us. Please try again later.",
            "error_code": code,
        }
        if retry_after_seconds is not None:
            detail["retry_after_seconds"] = retry_after_seconds
        if upgrade_url:
            detail["upgrade_url"] = upgrade_url
        raise HTTPException(status_code=429, detail=detail)
    if resp.status_code != 200:
        code = generate_error_code()
        log("ERROR", "figma import failed", status=resp.status_code, body=resp.text[:200], error_code=code)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "We couldn't import that frame. It may be private or the link may have expired.",
                "error_code": code,
            },
        )

    try:
        data = resp.json()
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "figma import parse failed", error=str(e), error_code=code)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "We couldn't import that frame. Please try again.",
                "error_code": code,
            },
        )

    # Fetch thumbnail image for the frame
    thumbnail_url = None
    try:
        img_resp = await httpx.AsyncClient().get(
            f"{FIGMA_API_BASE}/images/{file_key}",
            params={"ids": node_id, "format": "png", "scale": 2},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if img_resp.status_code == 200:
            img_data = img_resp.json()
            images = img_data.get("images", {})
            thumbnail_url = images.get(node_id)
    except Exception as e:
        log("WARN", "figma thumbnail fetch failed", error=str(e))

    # Extract frame metadata
    frame_name = None
    frame_width = None
    frame_height = None
    child_count = 0
    for node_data in data.get("nodes", {}).values():
        if isinstance(node_data, dict) and "document" in node_data:
            doc = node_data["document"]
            frame_name = doc.get("name")
            bbox = doc.get("absoluteBoundingBox", {})
            frame_width = bbox.get("width")
            frame_height = bbox.get("height")
            child_count = len(doc.get("children", []))
            break

    warnings = _validate_design_context(data)

    # Store in DB cache (survives restarts, 7-day TTL)
    frame_width_int = int(frame_width) if frame_width else None
    frame_height_int = int(frame_height) if frame_height else None
    store_figma_design_cache(
        file_key=file_key,
        node_id=node_id,
        design_context=data,
        thumbnail_url=thumbnail_url,
        frame_name=frame_name,
        frame_width=frame_width_int,
        frame_height=frame_height_int,
        child_count=child_count,
    )
    log("INFO", "figma import completed", file_key=file_key[:8], warnings_count=len(warnings))
    return FigmaImportResponse(
        design_context=data,
        warnings=warnings,
        thumbnail_url=thumbnail_url,
        frame_name=frame_name,
        frame_width=frame_width_int,
        frame_height=frame_height_int,
        child_count=child_count,
        file_key=file_key,
        node_id=node_id,
    )


@router.get("/status")
async def figma_status(request: Request, bp_session: str | None = Cookie(default=None)) -> dict:
    """
    GET /api/figma/status

    Returns { "connected": true } if user/session has valid tokens, else { "connected": false }.
    Logged in: checks by user_id. Anonymous: checks by session cookie.
    """
    tokens = _get_figma_tokens_for_request(request, bp_session)
    return {"connected": tokens is not None}


@router.post("/disconnect")
async def figma_disconnect(request: Request, bp_session: str | None = Cookie(default=None)) -> dict:
    """
    POST /api/figma/disconnect

    Clears Figma OAuth tokens for the current user/session.
    Used when user wants to reconnect with a different account or tokens are stale.
    """
    user_id = get_current_user_id(request)
    if user_id:
        delete_figma_tokens(user_id=user_id)
        log("INFO", "figma disconnected by user", user_id=user_id[:8])
    elif bp_session:
        delete_figma_tokens(session_id=bp_session)
        log("INFO", "figma disconnected by session", session_id=bp_session[:8])
    return {"disconnected": True}
