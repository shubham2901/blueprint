# Blueprint Security Best Practices Report

**Generated:** 2026-02-24  
**Stack:** FastAPI (Python) backend + Next.js (TypeScript) frontend  
**Scope:** Full codebase security review

---

## Executive Summary

Blueprint has a generally solid security posture with good practices in cookie handling, input validation via Pydantic, and proper OAuth state management. The main areas requiring attention are:

1. **Medium: OpenAPI docs exposed in production** (information disclosure)
2. **Medium: CORS configuration allows all methods/headers** (overly permissive)
3. **Medium: Missing `Secure` flag on one cookie** (codegen session cookie)
4. **Low: Potential SSRF in scraper** (URL input from search results)
5. **Low: localStorage used for non-sensitive UI state** (acceptable)

No critical vulnerabilities were found.

---

## Critical Findings

*None identified.*

---

## High Severity Findings

*None identified.*

---

## Medium Severity Findings

### M-001: OpenAPI/Swagger docs exposed by default in production

**Rule ID:** FASTAPI-OPENAPI-001  
**Location:** `backend/app/main.py`, lines 55-59  
**Evidence:**
```python
app = FastAPI(
    title="Blueprint API",
    version="0.1.0",
    description="Product & market research tool...",
)
```

**Impact:** OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) are enabled by default, exposing all API endpoints, request/response schemas, and authentication patterns to potential attackers.

**Fix:** Disable docs in production:
```python
app = FastAPI(
    title="Blueprint API",
    version="0.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)
```

---

### M-002: CORS allows all methods and headers

**Rule ID:** FASTAPI-CORS-001  
**Location:** `backend/app/main.py`, lines 61-69  
**Evidence:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** While origins are properly configured from environment, allowing all methods (`["*"]`) and all headers (`["*"]`) is more permissive than necessary. Combined with `allow_credentials=True`, this increases attack surface.

**Fix:** Restrict to only required methods and headers:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-Id"],
)
```

---

### M-003: Session cookie missing `Secure` flag in codegen endpoint

**Rule ID:** FASTAPI-SESS-001  
**Location:** `backend/app/api/codegen.py`, lines 147-154  
**Evidence:**
```python
response.set_cookie(
    key=SESSION_COOKIE,
    value=session_id,
    max_age=60 * 60 * 24 * 30,
    httponly=True,
    samesite="lax",
    path="/",
)
```

**Impact:** The session cookie in `codegen.py` does not set `secure=True` for production, unlike the Figma OAuth cookies which use `secure=_is_secure()`. This cookie could be transmitted over HTTP in production.

**Fix:** Add conditional `secure` flag:
```python
response.set_cookie(
    key=SESSION_COOKIE,
    value=session_id,
    max_age=60 * 60 * 24 * 30,
    httponly=True,
    secure=settings.environment == "production",
    samesite="lax",
    path="/",
)
```

---

## Low Severity Findings

### L-001: Potential SSRF in scraper (limited risk)

**Rule ID:** FASTAPI-SSRF-001  
**Location:** `backend/app/scraper.py`, lines 42-62  
**Evidence:**
```python
async def scrape(url: str) -> str:
    """Scrape URL with Jina (primary) then BS4 (fallback)."""
```

**Impact:** The `scrape()` function accepts URLs that originate from search results (Tavily/Serper), not direct user input. However, if search results return malicious URLs pointing to internal services (`localhost`, `169.254.169.254` metadata endpoints, internal IPs), this could be exploited.

**Mitigation:** The risk is low because:
1. URLs come from search engine results, not direct user input
2. The function is only used internally for competitor scraping
3. Jina Reader acts as a proxy layer

**Recommended:** Add URL validation to block private IP ranges and metadata endpoints for defense-in-depth:
```python
from urllib.parse import urlparse
import ipaddress

def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except ValueError:
        pass  # hostname is not an IP
    # Block cloud metadata endpoints
    if parsed.hostname in ("169.254.169.254", "metadata.google.internal"):
        return False
    return True
```

---

### L-002: localStorage used for UI state (acceptable)

**Rule ID:** REACT-AUTH-001 (partial)  
**Location:** `frontend/app/page.tsx`, lines 66-101  
**Evidence:**
```typescript
localStorage.setItem("bp_figma_connected", "1");
localStorage.setItem("bp_figma_url", figmaUrl.trim());
```

**Impact:** localStorage is used for non-sensitive UI preferences (Figma URL, connection status flag). This is acceptable since:
1. No auth tokens or secrets are stored
2. The stored data is purely for UX convenience
3. Actual auth state is verified server-side

**Status:** No action required.

---

### L-003: sessionStorage for pending prompt (acceptable)

**Rule ID:** REACT-AUTH-001 (partial)  
**Location:** `frontend/app/research/page.tsx`, line 23  
**Evidence:**
```typescript
sessionStorage.setItem("bp_pending_prompt", trimmed);
```

**Impact:** Session-scoped storage of a research prompt is acceptable and poses no security risk.

**Status:** No action required.

---

## Security Posture Summary

### What's Done Well

| Control | Status | Evidence |
|---------|--------|----------|
| **Cookie security (Figma)** | ✅ Good | `httponly=True`, `secure=_is_secure()`, `samesite="lax"` |
| **OAuth CSRF protection** | ✅ Good | State parameter validated in callback |
| **Input validation** | ✅ Good | Pydantic models throughout |
| **Rate limiting** | ✅ Good | slowapi configured per-endpoint |
| **Request ID correlation** | ✅ Good | X-Request-Id middleware |
| **Error codes for users** | ✅ Good | BP-XXXXXX format, no stack traces |
| **SQL injection prevention** | ✅ Good | Using Supabase ORM, no raw SQL |
| **No command injection sinks** | ✅ Good | No subprocess/os.system usage |
| **No XSS sinks in React** | ✅ Good | No dangerouslySetInnerHTML |
| **NEXT_PUBLIC_ usage** | ✅ Good | Only API_URL exposed (non-secret) |

### Recommendations

1. **High Priority:** Fix M-003 (secure flag on codegen cookie)
2. **Medium Priority:** Fix M-001 (disable docs in production)
3. **Medium Priority:** Fix M-002 (restrict CORS methods/headers)
4. **Low Priority:** Add SSRF URL validation to scraper

---

## Threat Model Summary

### Trust Boundaries

1. **Internet → Backend API** (CORS-protected, rate-limited)
2. **Backend → Supabase** (service key auth)
3. **Backend → Figma API** (OAuth tokens)
4. **Backend → LLM providers** (API keys)
5. **Backend → Search providers** (API keys)
6. **Frontend → Backend** (session cookies)

### Assets at Risk

| Asset | Risk | Protection |
|-------|------|------------|
| Figma OAuth tokens | Medium | Stored in DB, per-user/session |
| LLM API keys | High | Server-only, not exposed |
| User prompts/research | Low | Anonymous V0, no PII |
| Generated prototypes | Low | Session-scoped storage |

### Attacker Model

- **Remote attacker:** Can make API requests, attempt CSRF, inject via search results
- **Non-capabilities:** Cannot access backend env vars, cannot bypass OAuth state validation

---

## Files Reviewed

- `backend/app/main.py` - App factory, middleware
- `backend/app/api/figma.py` - OAuth flow, token handling
- `backend/app/api/codegen.py` - Code generation endpoint
- `backend/app/scraper.py` - Web scraping
- `backend/app/db.py` - Database operations
- `backend/app/llm.py` - LLM calls
- `frontend/app/page.tsx` - Landing page
- `frontend/lib/api.ts` - API client

---

**Report generated by security audit on 2026-02-24**
