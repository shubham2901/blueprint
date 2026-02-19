# Phase 01: Figma OAuth — User Setup Required

**Generated:** 2025-02-19
**Phase:** 01-shell-landing-figma-import
**Status:** Incomplete

Complete these items for Figma OAuth to function.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `FIGMA_CLIENT_ID` | Figma → Settings → Apps & integrations → Develop → OAuth 2 → Client ID | `backend/.env` |
| [ ] | `FIGMA_CLIENT_SECRET` | Figma → Settings → Apps & integrations → Develop → OAuth 2 → Client secret | `backend/.env` |
| [ ] | `FIGMA_REDIRECT_URI` | Must match exactly (backend callback URL) | `backend/.env` |

**FIGMA_REDIRECT_URI values:**
- **Local dev:** `http://localhost:8000/api/figma/oauth/callback`
- **Production:** `https://[your-backend-domain]/api/figma/oauth/callback`

## Account Setup

- [ ] **Create OAuth 2 app in Figma**
  - URL: Figma → Settings → Apps & integrations → Develop
  - Create new app or use existing
  - Skip if: Already have Figma app

## Dashboard Configuration

- [ ] **Add redirect URI in Figma app**
  - Location: Figma app settings → OAuth 2
  - Add redirect URI: `http://localhost:8000/api/figma/oauth/callback` (for dev)
  - Must match `FIGMA_REDIRECT_URI` character-for-character

- [ ] **Create figma_tokens table in Supabase**
  - Run the SQL from PLAN.md Part 5 (figma_tokens table)
  - Or: Supabase Dashboard → SQL Editor → paste and run

## Verification

After completing setup:

```bash
# Check env vars
grep FIGMA backend/.env

# Start backend
cd backend && uvicorn app.main:app --reload

# Test OAuth start (should redirect to Figma)
curl -I "http://localhost:8000/api/figma/oauth/start"

# Test status (should return {"connected": false} without session)
curl http://localhost:8000/api/figma/status
```

Expected: OAuth start redirects to figma.com; status returns JSON.

---

**Once all items complete:** Mark status as "Complete" at top of file.
