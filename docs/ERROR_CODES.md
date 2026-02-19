# Error Codes — Internal Documentation

User-facing errors show a **friendly message** plus **(Ref: BP-XXXXXX)**. The code is generated at runtime and logged on the backend. Use it to correlate user reports with logs.

## Lookup

```bash
# Find the error in logs
grep "BP-XXXXXX" backend/logs/
# or
grep "error_code=BP-XXXXXX" ...
```

Each log line includes `error=`, `operation=`, and context. The code links user-visible ref to the backend log entry.

## Error Scenarios → User Message

| Scenario | User sees | Internal details |
|----------|-----------|------------------|
| Figma OAuth cancelled | "Connection was cancelled. Try connecting again. (Ref: BP-XXXXXX)" | User closed Figma OAuth popup or denied access |
| Figma OAuth failed | "We couldn't connect to Figma. Please try again. (Ref: BP-XXXXXX)" | Token exchange failed, invalid client, network error |
| Invalid Figma URL | "That doesn't look like a valid Figma frame URL. Check the link and try again. (Ref: BP-XXXXXX)" | URL missing file_key or node_id, wrong format |
| Figma import failed | "We couldn't import that frame. It may be private or the link may have expired. (Ref: BP-XXXXXX)" | 403, 404, rate limit, or API error |
| Code generation failed | "We're having trouble generating the prototype. Please try again. (Ref: BP-XXXXXX)" | LLM error, timeout, validation failure |
| Preview compile error | "Preview couldn't load. We've restored your last version. (Ref: BP-XXXXXX)" | Sandpack compile failed; retry attempted; fallback applied |
| Session load failed | "We couldn't restore your session. Start a new prototype. (Ref: BP-XXXXXX)" | DB read failed, session not found |
| Unknown error | "Something unexpected happened. Please try again. (Ref: BP-XXXXXX)" | Unhandled exception; check full stack in logs |

## Implementation

- **Backend:** `generate_error_code()` from `config.py` — returns `BP-` + 6 hex chars
- **Log:** Always include `error_code=code` in the ERROR log line
- **Response:** Include `error_code` in SSE `ErrorEvent` / `BlockErrorEvent` or REST error payload
- **Frontend:** Show friendly message + `(Ref: {error_code})` in small muted text; never show raw error, stack trace, or provider names
