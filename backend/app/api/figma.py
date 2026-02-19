"""
Blueprint Backend — Figma OAuth & Import API

OAuth 2 flow: start → Figma consent → callback (token exchange) → redirect to frontend.
Status endpoint for frontend to check connection state.
"""

import base64
import secrets
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Request, Response
from fastapi.responses import RedirectResponse

from app.config import generate_error_code, log, settings
from app.db import get_figma_tokens, store_figma_tokens

router = APIRouter(prefix="/api/figma", tags=["figma"])

FIGMA_AUTH_URL = "https://www.figma.com/oauth"
FIGMA_TOKEN_URL = "https://api.figma.com/v1/oauth/token"
SCOPES = "file_content:read,file_metadata:read"
STATE_COOKIE = "bp_figma_state"
SESSION_COOKIE = "bp_session"
STATE_MAX_AGE = 300  # 5 minutes
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _is_secure() -> bool:
    return settings.environment == "production"


@router.get("/oauth/start")
async def oauth_start(response: Response) -> RedirectResponse:
    """
    GET /api/figma/oauth/start

    Generates state, stores in cookie, redirects to Figma OAuth consent.
    """
    if not settings.figma_client_id:
        log("ERROR", "figma oauth start failed", error="FIGMA_CLIENT_ID not configured", error_code="BP-CONFIG")
        redirect_url = f"{settings.frontend_url}?figma_error=1&error_code=BP-CONFIG"
        return RedirectResponse(url=redirect_url, status_code=302)

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
        samesite="lax",
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

    # User denied or error from Figma
    if error:
        code_err = generate_error_code()
        log("ERROR", "figma oauth callback error", error=error, error_code=code_err)
        resp = RedirectResponse(url=f"{frontend_url}?figma_error=1&error_code={code_err}", status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

    # Validate state (CSRF)
    if not state or not bp_figma_state or state != bp_figma_state:
        code_err = generate_error_code()
        log("ERROR", "figma oauth state mismatch", error_code=code_err)
        resp = RedirectResponse(url=f"{frontend_url}?figma_error=1&error_code={code_err}", status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

    if not code:
        code_err = generate_error_code()
        log("ERROR", "figma oauth callback missing code", error_code=code_err)
        resp = RedirectResponse(url=f"{frontend_url}?figma_error=1&error_code={code_err}", status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

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
        resp = RedirectResponse(url=f"{frontend_url}?figma_error=1&error_code={code_err}", status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

    if token_resp.status_code != 200:
        code_err = generate_error_code()
        log("ERROR", "figma token exchange failed", status=token_resp.status_code, body=token_resp.text[:200], error_code=code_err)
        resp = RedirectResponse(url=f"{frontend_url}?figma_error=1&error_code={code_err}", status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

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
        resp = RedirectResponse(url=f"{frontend_url}?figma_error=1&error_code={code_err}", status_code=302)
        resp.delete_cookie(STATE_COOKIE, path="/")
        return resp

    # Generate or reuse session_id
    session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())

    # Store tokens (sync call)
    from datetime import datetime, timedelta, timezone
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    store_figma_tokens(session_id, access_token, refresh_token, expires_at)

    log("INFO", "figma oauth complete", session_id=session_id[:8])

    resp = RedirectResponse(url=f"{frontend_url}?figma_connected=1", status_code=302)
    resp.delete_cookie(STATE_COOKIE, path="/")
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/status")
async def figma_status(bp_session: str | None = Cookie(default=None)) -> dict:
    """
    GET /api/figma/status

    Returns { "connected": true } if session has valid tokens, else { "connected": false }.
    No auth required — frontend uses this to set figmaConnected state.
    """
    if not bp_session:
        return {"connected": False}
    tokens = get_figma_tokens(bp_session)
    return {"connected": tokens is not None}
