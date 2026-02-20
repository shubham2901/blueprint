---
phase: 02-code-generation
plan: 04
subsystem: api
tags: [codegen, figma, esbuild-py, vision-llm, design-to-code]

# Dependency graph
requires:
  - phase: 02-code-generation
    provides: transform_design_context, call_llm_vision, create_prototype_session
provides:
  - POST /api/code/generate — design context → transform → vision LLM → validate → store
  - GET /api/code/session — session restore for bp_session cookie
  - build_design_to_code_prompt
  - FigmaImportResponse/CodeGenerateRequest file_key, node_id
affects: [02-05-frontend-wiring]

# Tech tracking
tech-stack:
  added: [esbuild-py]
  patterns: [JSX validation via esbuild transform, Figma SVG export for icons]

key-files:
  created: [backend/app/api/codegen.py]
  modified: [backend/app/api/figma.py, backend/app/models.py, backend/app/prompts.py, backend/app/db.py, backend/app/main.py, backend/requirements.txt]

key-decisions:
  - "esbuild-py for JSX validation — pure Python, no Node required"
  - "Figma tokens required for code gen (401 if not connected) — same pattern as import"
  - "create_prototype_session accepts optional status param (generating|pending|ready|error)"

patterns-established:
  - "Code gen flow: transform → thumbnail base64 → optional icon SVGs → prompt → vision LLM → strip_code_fences → validate → store"
  - "Auto-retry once on JSX validation failure before surfacing error"

requirements-completed: [CODE-01]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 02 Plan 04: Code Generation Endpoint Summary

**End-to-end backend flow for design-to-code: POST /api/code/generate, design-to-code prompt, JSX validation via esbuild-py, Figma SVG export for icons, session storage**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-20T09:55:30Z
- **Completed:** 2026-02-20T09:58:13Z
- **Tasks:** 4
- **Files modified:** 7

## Accomplishments

- FigmaImportResponse and CodeGenerateRequest extended with file_key, node_id for Figma API calls
- build_design_to_code_prompt(transformed_context) — role, constraints, output format, context JSON
- POST /api/code/generate: transform → vision LLM → validate JSX → store; auto-retry once on failure
- GET /api/code/session: return prototype session for bp_session cookie
- Figma SVG export for VECTOR/BOOLEAN_OPERATION nodes, passed to prompt as icons dict
- esbuild-py for JSX validation, comprehensive structured logging

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Figma import response and CodeGenerateRequest** - `498e16c` (feat)
2. **Task 2: Design-to-code prompt** - `c9e75b7` (feat)
3. **Task 3: Code generation endpoint** - `0f26a72` (feat)
4. **Task 4: Figma SVG export for icons** - `0f26a72` (feat, bundled with Task 3)

## Files Created/Modified

- `backend/app/api/codegen.py` — created: POST /generate, GET /session, SVG export, JSX validation
- `backend/app/api/figma.py` — set file_key, node_id in import response
- `backend/app/models.py` — file_key, node_id on FigmaImportResponse, CodeGenerateRequest
- `backend/app/prompts.py` — build_design_to_code_prompt
- `backend/app/db.py` — create_prototype_session status param
- `backend/app/main.py` — register codegen router
- `backend/requirements.txt` — esbuild-py

## Decisions Made

- **esbuild-py:** Used esbuild_py package (import esbuild_py) for JSX validation; no Node required in backend
- **Tokens required:** Same as figma import — 401 if no Figma tokens; needed for SVG export
- **Session cookie:** Set bp_session if missing when creating new session (for anonymous users)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Self-Check: PASSED

- [x] backend/app/api/codegen.py exists
- [x] Commits 498e16c, c9e75b7, 0f26a72 exist
- [x] POST /api/code/generate returns 401 without tokens
- [x] GET /api/code/session returns 404 without cookie

## Next Phase Readiness

- Code generation endpoint ready for frontend wiring (02-05)
- Frontend will pass design_context, thumbnail_url, frame_metadata, file_key, node_id from import result
- Frontend types need file_key, node_id (per plan: 02-05)

---
*Phase: 02-code-generation*
*Completed: 2026-02-20*
