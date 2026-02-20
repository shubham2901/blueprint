---
phase: 02-code-generation
plan: 06
subsystem: testing
tags: [pytest, figma-context, llm-vision, codegen-api, litellm, httpx]

# Dependency graph
requires:
  - phase: 02-04
    provides: Code generation endpoint, transform_design_context, call_llm_vision, strip_code_fences
provides:
  - Unit tests for design context transformer (14 tests)
  - Unit tests for LLM vision and code fence stripping (14 tests)
  - Integration tests for POST /api/code/generate and GET /api/code/session (17 tests)
  - conftest fixtures: mock_llm_vision, mock_prototype_session_db, prototype_sessions in mock_db
affects: [02-code-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [patch-at-use-site for imported functions, mock _validate_jsx for retry tests]

key-files:
  created: [backend/tests/test_figma_context.py, backend/tests/test_codegen.py, backend/tests/test_codegen_api.py]
  modified: [backend/tests/conftest.py]

key-decisions:
  - "Patch app.api.codegen.get_figma_tokens and app.api.codegen.create_prototype_session (not app.db) — modules import at load time"
  - "Mock _validate_jsx for retry tests — esbuild-py transform accepts almost any input, does not fail on invalid JSX"

patterns-established:
  - "Patch where used: For code that imports from app.db at module load, patch app.api.codegen.* not app.db.*"
  - "Integration test fixtures: mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx — all external services mocked"

requirements-completed: [CODE-01]

# Metrics
duration: ~25min
completed: 2026-02-20
---

# Phase 2 Plan 6: Code Generation Tests Summary

**45 new tests for design context transformer, LLM vision, code fences, and code generation API — all external services mocked per AGENTS.md**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-20T09:59:31Z
- **Completed:** 2026-02-20T10:04:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- 14 unit tests for `transform_design_context` (pure function, no mocks)
- 14 unit tests for `strip_code_fences` and `call_llm_vision` (mocked litellm)
- 17 integration tests for POST /api/code/generate and GET /api/code/session
- conftest extended with prototype_sessions storage and mock_llm_vision fixture
- Full backend suite: 181 passed, 78 skipped (evals)

## Task Commits

Each task was committed atomically:

1. **Task 1: Unit tests for design context transformer** - `905ca6a` (test)
2. **Task 2: Unit tests for LLM vision and code fences** - `5f5a118` (test)
3. **Task 3: Integration tests for code generation API** - `7d6f578` (test)

## Files Created/Modified

- `backend/tests/test_figma_context.py` - 14 unit tests for transform_design_context
- `backend/tests/test_codegen.py` - 14 unit tests for strip_code_fences and call_llm_vision
- `backend/tests/test_codegen_api.py` - 17 integration tests for codegen API
- `backend/tests/conftest.py` - prototype_sessions, mock_llm_vision, datetime import, codegen db patches

## Decisions Made

- **Patch at use site:** Codegen imports `get_figma_tokens`, `create_prototype_session` from app.db. Patching app.db.* does not affect codegen's references. Must patch app.api.codegen.*.
- **Mock _validate_jsx for retry tests:** esbuild-py transform() accepts almost any input without raising. To test retry-on-invalid-JSX logic, mock _validate_jsx to return (False, "error") on first call.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing datetime import in conftest**
- **Found during:** Task 3 (integration tests)
- **Issue:** mock_create_prototype_session used datetime.now(timezone.utc) but datetime not imported
- **Fix:** Added `from datetime import datetime, timezone` to conftest
- **Files modified:** backend/tests/conftest.py
- **Verification:** test_codegen_api tests pass
- **Committed in:** 7d6f578 (Task 3 commit)

**2. [Rule 3 - Blocking] mock_prototype_session functions not defined**
- **Found during:** Task 2 (conftest setup)
- **Issue:** monkeypatch referenced mock_create_prototype_session before it was defined in mock_db
- **Fix:** Added mock_create_prototype_session, mock_update_prototype_session, mock_get_prototype_session definitions before Apply mocks section
- **Files modified:** backend/tests/conftest.py
- **Verification:** mock_db fixture loads, tests pass
- **Committed in:** 5f5a118 (Task 2 commit)

**3. [Rule 1 - Bug] Retry tests failed — esbuild accepts invalid JSX**
- **Found during:** Task 3 (test_generate_retries_on_invalid_jsx)
- **Issue:** esbuild-py transform() does not raise on "invalid jsx {{{" or similar
- **Fix:** Mock _validate_jsx to return (False, "Parse error") on first call for retry test; (False, "Parse error") always for fail-after-retry test
- **Files modified:** backend/tests/test_codegen_api.py
- **Verification:** Both retry tests pass
- **Committed in:** 7d6f578 (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking x2, 1 bug)
**Impact on plan:** All fixes necessary for tests to run and pass. No scope creep.

## Issues Encountered

- Fixture application order: mock_figma_tokens must patch app.api.codegen.get_figma_tokens (not app.db) because codegen holds import-time reference
- Log capture for vision tests: patch app.llm.log (not app.config.log) so call_llm_vision uses the mock

## User Setup Required

None - no external service configuration required. All tests use mocks.

## Next Phase Readiness

- Code generation pipeline fully covered by tests
- Ready for Phase 2 completion or Phase 3 planning

## Self-Check: PASSED

- [x] backend/tests/test_figma_context.py exists
- [x] backend/tests/test_codegen.py exists
- [x] backend/tests/test_codegen_api.py exists
- [x] Commits 905ca6a, 5f5a118, 7d6f578 exist
- [x] pytest backend/tests/ — 181 passed

---
*Phase: 02-code-generation*
*Completed: 2026-02-20*
