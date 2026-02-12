# Blueprint — Tech Debt & Deferred Decisions

This file tracks everything intentionally deferred from V0. Each item includes context on why it was deferred, what the V0 workaround is (if any), and the migration path when it's time to implement.

Items are grouped by category and tagged with a target version: **V1** (next release), **V2** (later), **V2+** (eventually/indefinitely).

---

## Auth and Users

### Google OAuth — V1
- **What**: Supabase Auth with Google sign-in + magic link email
- **V0 workaround**: Fully anonymous. No accounts, no login.
- **Migration path**: Activate Supabase Auth, add `user_id UUID` column to `journeys` table, create JWT validation middleware in FastAPI, add `AuthModal.tsx` wiring (UI shell already built in V0).
- **Risk if deferred too long**: No way to associate journeys with returning users. V0 data is test data and will likely be abandoned.

### Anonymous Session Migration — V1
- **What**: When an anonymous user signs up, link their existing anonymous journeys to their new account.
- **V0 workaround**: None. Anonymous journeys are not linked to anything.
- **Migration path**: Before auth, add `anonymous_token` column to `journeys`. Store a UUID in localStorage. On signup, UPDATE journeys SET user_id = new_user WHERE anonymous_token = stored_token.
- **Dependency**: Requires Google OAuth to be implemented first.

### Session Limits — V1
- **What**: Track and limit free sessions per anonymous user (IP-based or localStorage token).
- **V0 workaround**: No limits. Everyone gets unlimited access.
- **Migration path**: Add session counter to journeys (count by anonymous_token or IP). Check on each new research request.
- **Note**: Founder explicitly said no server-side IP tracking for now. Use localStorage token approach when ready.

### Rate Limiting Per User — V1
- **What**: Per-user request quotas (e.g., 20 researches/day for free tier, 100 for paid).
- **V0 workaround**: Global rate limiting via slowapi (per-IP, same limit for everyone).
- **Migration path**: After auth exists, replace IP-based rate limiting with user_id-based.
- **Dependency**: Requires auth.

### Row Level Security (RLS) — V1
- **What**: Supabase RLS policies so users only see their own journeys.
- **V0 workaround**: None needed — V0 is anonymous. All journeys are globally visible (but there's no listing endpoint that shows other people's data).
- **Migration path**: Add RLS policies on journeys and journey_steps tables. Standard Supabase pattern.
- **Dependency**: Requires auth + user_id column.

### User Profiles — V1
- **What**: Store user preferences, saved settings, display name.
- **V0 workaround**: None. No users, no profiles.
- **Migration path**: Add `profiles` table with FK to auth.users. Supabase has a standard pattern for this with a trigger on user creation.

---

## LLM and AI

### LLM Tiers — V1
- **What**: Free/smart/advanced subscription tiers. Each tier maps to a different model chain (e.g., free → Gemini Flash, smart → Gemini Pro, advanced → Claude Opus).
- **V0 workaround**: Single tier, single fallback chain.
- **Migration path**: Expand `LLM_CONFIG` in `config.py` from a single `fallback_chain` to a dict of `{ tier: fallback_chain }`. Add tier lookup from user's subscription. Core `llm.py` fallback logic stays identical.
- **Dependency**: Requires auth + subscription/payment system.

### LLM Budget Tracking — V1
- **What**: Per-provider monthly spend tracking with configurable budgets. Alert when approaching limits.
- **V0 workaround**: Reactive fallback — no budget checking. If a provider fails, switch. No spend tracking.
- **Migration path**: Add `llm_budget` table (provider, tier, period, total_cost, total_requests). After each litellm call, record the cost (litellm provides this in the response). Check against budget thresholds.
- **Trade-off considered**: Pre-call budget checks add ~5-20ms latency per LLM request (DB read). The founder explicitly chose reactive over proactive. If budget tracking is added, it should be async (log after response, don't block before request).

### YAML-Based LLM Config — V1
- **What**: Move LLM configuration from Python dict to a YAML file. Better for non-developers to edit, version-controlled, supports complex multi-tier definitions.
- **V0 workaround**: Python dict in `config.py`. Simple, works for single tier.
- **Migration path**: Add `llm_config.yaml`, add YAML loader in `config.py`, update `llm.py` to read from parsed YAML instead of dict. Same data structure, different format.
- **When to do it**: When the tier system arrives and the config gets complex enough that a Python dict is hard to read.

### Per-Query Model Selector — V1+
- **What**: Let users pick model quality per research session (like ChatGPT's model dropdown).
- **V0 workaround**: Single model for everyone.
- **Migration path**: Add `model_tier` parameter to `/api/research` request. Frontend adds a dropdown. Backend routes to the appropriate chain.
- **Dependency**: Requires tier system and possibly auth (to enforce limits per tier).

### Edge AI (Browser-Side) — V2+
- **What**: Run small models in the browser for input classification, autocomplete, quick suggestions. Technologies: Chrome Prompt API, WebLLM, ONNX Runtime Web.
- **V0 workaround**: All AI processing happens on the backend.
- **Why deferred**: Chrome's Prompt API is experimental and Chrome-only. WebLLM has 2-8s cold start and requires 1-4GB model download. Device fragmentation makes it unreliable. The founder agreed to skip this.
- **When to revisit**: When Chrome Prompt API reaches stable status and works on 80%+ of target users' browsers.

### Multiple Concurrent LLM Providers — V2
- **What**: Use different models for different tasks within the same research (e.g., fast model for classification, strong model for deep analysis).
- **V0 workaround**: Same model for all tasks.
- **Migration path**: Add `task_type` parameter to `llm.py` calls. Map task types to models in config.

---

## Product Modules

These are from the product roadmap in [PLAN.md](PLAN.md). Each new module follows the same pattern: add a prompt in `prompts.py`, a block type in `models.py`, and a step in `api/research.py`.

### B3: Feature Extractor — V1
- **What**: Deep feature lists per product (not just a summary, but structured feature-by-feature breakdown).
- **V0 has**: Brief features summary in product profiles.

### B4: Pricing Extractor — V1
- **What**: Detailed pricing tiers, breakdowns, comparison-ready pricing data.
- **V0 has**: Estimated pricing model (one line).

### B5: Sentiment Analyzer — V1
- **What**: Public reviews from Reddit, Product Hunt, app stores. Sentiment scoring.
- **V0 has**: Reddit sentiment is qualitative (LLM-summarized text). No numeric scoring or multi-source reviews.

### B6: Feature Comparator — V2
- **What**: Side-by-side feature matrix for selected competitors.
- **Depends on**: B3 Feature Extractor.

### B7: Pricing Comparator — V2
- **What**: Side-by-side pricing table for selected competitors.
- **Depends on**: B4 Pricing Extractor.

### B8: Market Landscaper — V2
- **What**: Full categorized market map with positioning.
- **Depends on**: B2 Competitor Finder + B3 + B5.

### Persona Generator — V2+
- **What**: Generate user personas from public data (reviews, social media, job postings).

### JTBD Identifier — V2+
- **What**: Jobs-to-be-done framework analysis from user reviews and product messaging.

### PRD Writer — V2+
- **What**: Auto-generate product requirements documents from accumulated research data.

---

## Architecture and Code Quality

### Dependency Injection — V1
- **What**: FastAPI `Depends()` layer for database, LLM client, and auth. Enables clean testing with mock dependencies.
- **V0 workaround**: Direct imports. `from app.db import get_supabase_client` called inline.
- **Migration path**: Wrap existing functions in `Depends()`. Change endpoint signatures from `def endpoint():` to `def endpoint(db=Depends(get_db)):`. Additive change, no breaking refactor.
- **When to do it**: When writing proper tests that need mocked dependencies.

### Auto-Generated API Types — V1
- **What**: Generate TypeScript types from FastAPI's OpenAPI schema using `openapi-typescript`. Prevents FE/BE type drift.
- **V0 workaround**: Manual `types.ts` file in frontend. Structured so it can be replaced by codegen output.
- **Migration path**: Install `openapi-typescript`, point it at `/openapi.json`, replace `types.ts` with generated output. Same import paths, same type names if structured correctly.
- **When to do it**: After the API stabilizes (post-Phase 4). Running codegen on a fast-changing API during vibecoding creates churn.

### Abstract Provider Pattern — V1+
- **What**: Base class / protocol for search providers, scraper providers, LLM providers. Enables clean polymorphism.
- **V0 workaround**: Simple functions with try/except fallback. `serper_search()` → fail → `duckduckgo_search()`.
- **Why deferred**: For 2 providers, abstract classes add ~20 lines of boilerplate with zero practical benefit. A third provider is equally easy to add as a new function.
- **When to do it**: When there are 4+ providers for any category.

### Formal Idempotency Middleware — V1
- **What**: Server-side request deduplication with persistent idempotency keys. Client sends `Idempotency-Key` header, server returns cached response for duplicate keys.
- **V0 workaround**: Frontend disables button on click. Backend tracks in-memory active researches.
- **Migration path**: Add middleware that checks/stores idempotency keys in Supabase or Redis.

### Design Token Extraction — V1
- **What**: Separate `tokens.ts` file that feeds `tailwind.config.ts` + CSS variables. Proper design system architecture.
- **V0 workaround**: All tokens directly in `tailwind.config.ts`. One file to edit, but no programmatic access to tokens.
- **When to do it**: When dark mode or multiple themes are needed (tokens file can export multiple themes).

### Background Job Queue — V2
- **What**: Celery or ARQ for processing research requests as background jobs. Needed when concurrent users exceed what FastAPI async can handle on a single process.
- **V0 workaround**: FastAPI async (`asyncio.gather`) handles concurrency. Research runs in the request handler.
- **When to do it**: When there are 50+ concurrent research sessions and Railway starts showing memory pressure.

### Redis Caching Layer — V2
- **What**: In-memory cache (Redis) in front of Supabase for hot product data. Sub-millisecond reads for popular products.
- **V0 workaround**: Supabase PostgreSQL handles all caching (product TTL check). Adequate for V0 traffic.
- **When to do it**: When Supabase reads become a bottleneck (100s of concurrent users hitting the same products).

### SSE Event Envelope / Versioning — V1
- **What**: Add `schema_version`, `event_id`, `seq` (sequence number), and `timestamp` to every SSE event. Enables event replay, debugging, and forward-compatible protocol evolution.
- **V0 workaround**: Events are typed (`type` field) but have no versioning or sequence tracking. Events are ordered within a single stream but ordering across reconnects is not guaranteed.
- **Migration path**: Wrap all SSE events in an envelope: `{ schema_version: "1", event_id: "uuid", seq: 5, ts: "ISO", payload: { ...existing event... } }`. Frontend ignores unknown `schema_version` values gracefully.
- **When to do it**: When the API has multiple frontend clients or when debugging event ordering becomes painful.

### Run-Based Cancel Endpoint — V1
- **What**: `POST /api/research/{journey_id}/cancel` to abort an in-progress research pipeline.
- **V0 workaround**: No cancellation. If the user navigates away, the SSE stream is dropped (client disconnect) and the backend finishes the pipeline in the background (results still saved to DB).
- **Migration path**: Add endpoint that sets a cancellation flag. Pipeline checks the flag between steps and aborts early if set.
- **When to do it**: When research pipelines become long enough that users want to abort mid-run.

### DB-Backed Request Deduplication — V1
- **What**: Use a database table or Redis to track active research sessions, instead of the in-memory `_active_researches` dict.
- **V0 workaround**: In-memory dict (lost on restart). Frontend button disable handles 99% of cases.
- **Migration path**: Add `status` enum to `journeys` table (`queued`, `running`, `waiting_input`, `completed`, `failed`). Check journey status before starting a new pipeline for the same journey.
- **When to do it**: When running multiple backend workers or when Railway restarts become frequent enough to cause duplicate runs.

### Structured Logging — V1
- **What**: JSON-formatted structured logs with `structlog`. Correlation IDs (`journey_id`, `step_type`, provider) on every log line. Failure telemetry table for tracking error patterns.
- **V0 workaround**: Python `print()` statements and Railway's built-in log viewer.
- **Migration path**: Replace `print()` with `structlog` calls. Add `journey_id` as a context variable. Configure JSON output for Railway.
- **When to do it**: When debugging intermittent provider failures or scraper issues becomes time-consuming.

### Multi-Instance Support — V1
- **What**: Support multiple backend workers/instances. Requires externalizing all in-memory state (dedup dict, LLM provider cache, scraper semaphore).
- **V0 workaround**: Single uvicorn worker. All in-memory state is per-process. See ARCHITECTURE.md Section 7 (Single-Instance Assumption).
- **Migration path**: Move dedup to Redis or DB. Read LLM state from DB on each request (or use Redis cache with short TTL). Use a distributed semaphore for scraper concurrency.
- **When to do it**: When traffic requires `--workers N` or horizontal scaling on Railway.

### Abuse Protection Beyond Rate Limiting — V1
- **What**: Anonymous client tokens + soft quotas + per-token throttles. Prevents a single anonymous user from burning through expensive API quotas.
- **V0 workaround**: Global IP-based rate limiting via slowapi (same limit for everyone).
- **Migration path**: Generate anonymous token (UUID) on first visit, store in localStorage. Backend tracks usage per token. Enforce soft limits (e.g., 10 researches/day per token).
- **When to do it**: Before any public launch or when API costs become a concern. Ties into the auth migration (V1 auth replaces anonymous tokens with real user IDs).

### Block-Level Retry — V1
- **What**: Retry a single failed block (e.g., one product profile) without re-running the entire research pipeline.
- **V0 workaround**: "Try again" re-runs the full pipeline from scratch.
- **Migration path**: Add `POST /api/research/{journey_id}/retry-block` with a `block_id` or `product_name` parameter. Backend re-runs only the scrape+analyze step for that product.
- **When to do it**: When partial failures are common enough that full re-runs feel wasteful.

---

## Data and Storage

### Infinite Canvas / Tree Journey Model — V2+
- **What**: Replace linear `step_number` with `parent_step_id` tree structure. Users can branch from any step, creating a research tree.
- **V0 workaround**: Linear journey model. Steps are ordered by `step_number`. No branching.
- **Migration path**: Add `parent_step_id UUID` column (nullable FK to journey_steps.id). Drop `step_number`. Update queries from `ORDER BY step_number` to recursive CTEs.
- **Why deferred indefinitely**: Complex to implement via vibecoding. Founder confirmed this can wait for proper developers.

### Full-Text Search on Journeys — V2
- **What**: Search across all sessions for users with 100s of researches. PostgreSQL full-text search or Supabase FTS.
- **V0 workaround**: Simple list of journeys ordered by date.
- **Migration path**: Add `tsvector` column to journeys, create GIN index, add search endpoint.

### Search Result Caching — V1
- **What**: Cache raw Serper/DDG search results with 3-day TTL. "Personal finance app competitors" returns the same search results for 3 days.
- **V0 workaround**: No search caching. Every research request hits Serper.
- **Migration path**: Add `search_cache` table with query hash as key, result JSON, and TTL.

### Pagination — V1
- **What**: Paginate dashboard session list and long competitor lists.
- **V0 workaround**: Return all results. Acceptable for <100 journeys.
- **Migration path**: Add `offset` and `limit` params to API endpoints. Standard pagination.

### Data Export — V1
- **What**: Export Blueprint as Markdown, PDF, or Notion page.
- **V0 workaround**: None. Data only lives in the app.
- **Migration path**: Add `/api/export/:journey_id` endpoint. Markdown is straightforward. PDF via `weasyprint` or similar. Notion via Notion API.

### Multi-User Data Isolation — V1
- **What**: When auth arrives, ensure users only see their own journeys and can't access others'.
- **V0 workaround**: All journeys are anonymous and technically globally accessible (but there's no endpoint to browse other people's data by design).
- **Migration path**: Add `user_id` FK, add RLS policies, add `WHERE user_id = current_user` to all queries.
- **Dependency**: Requires auth.

---

## Frontend and UX

### Mobile Responsive Design — V1
- **What**: All current designs are desktop 1440px only. Mobile is a single-panel layout.
- **V0 workaround**: Desktop only. No mobile support.
- **Migration path**: Add Tailwind responsive classes. Sidebar becomes a slide-out drawer on mobile. Workspace takes full width.

### Dark Mode — V1+
- **What**: Dark variant of the Cozy Sand theme.
- **V0 workaround**: Light theme only.
- **Migration path**: Add dark theme tokens to tailwind.config (or extracted tokens.ts). Use Tailwind's `dark:` prefix.
- **Dependency**: May want design token extraction first.

### Keyboard Shortcuts — V1
- **What**: Cmd+Enter to send prompt, other power-user shortcuts shown in the designs.
- **V0 workaround**: Click-only interaction.
- **Migration path**: Add `useHotkeys` hook or simple `keydown` listeners.

### Copy as Markdown — V1
- **What**: "Copy as Markdown" button on the Blueprint tab (visible in Screen 6 design).
- **V0 workaround**: None. User can select + copy text manually.
- **Migration path**: Serialize Blueprint entries to Markdown string, copy to clipboard.

### Collapsed Sidebar — V0 Phase 5
- **What**: Screen 9 design shows a collapsed sidebar state (thin strip with logo + expand icon).
- **When**: Built in Phase 5 as part of polish. Included here as a V0 item that's in a later phase.

### WebSocket Support — V2+
- **What**: Real-time bidirectional communication for infinite canvas, live collaboration.
- **V0 workaround**: SSE (server → client only).
- **When to do it**: When infinite canvas or real-time collaboration becomes a priority.

### Accessibility — V1
- **What**: ARIA labels, keyboard navigation, screen reader support, focus management.
- **V0 workaround**: shadcn/ui components have basic accessibility built in (Radix Primitives). Custom components may lack ARIA labels.
- **Migration path**: Audit all interactive elements, add missing ARIA attributes, test with screen reader.

---

## Product Features (Deferred from V0)

### "Improve" Flow — V1
- **What**: A dedicated pipeline for users who want to improve an existing product — single-product deep dive without competitor analysis. Focuses on user pain points, feature gaps, and improvement opportunities for one specific product.
- **V0 workaround**: `improve` intent is detected by the classify step but redirected to the `explore` flow with an `intent_redirect` SSE event. The product becomes the anchor of an explore session.
- **Migration path**: Add new pipeline branch in `api/research.py` for `improve` intent. Add new prompts for single-product analysis, pain point extraction, improvement opportunities. Add new block types (`improvement_opportunities`, `pain_points`). Frontend already handles `intent_redirect` — replace redirect with the actual pipeline.
- **When to do it**: After V0 feedback confirms demand for the feature.

### Play Store / App Store Scraping — V0-EXPERIMENTAL / V1
- **What**: Scrape app store listings (iOS App Store, Google Play Store) for competitor discovery (similar apps), ratings, and metadata.
- **V0 status**: Trying in V0 using `google-play-scraper` and `app-store-scraper` Python libraries. `app_stores.py` exists with `search_play_store()`, `search_app_store()`, and `get_similar_apps()`. All functions wrapped in try/except — returns empty lists on failure. Pipeline continues without app store data.
- **V0 → V1 decision**: If the libraries work reliably and are fast (<5s per query), keep in V0. If flaky, rate-limited, or slow, defer full implementation to V1 and make the module return empty lists.
- **V1 expansion**: Add `app_reviews` block type for detailed review analysis. Add review sentiment scoring. Integrate into explore pipeline (run in parallel with web scraping).
- **When to do it**: Stabilize in V0 if possible; expand to reviews/sentiment in V1.

### App Screenshots — V1
- **What**: Scrape and display product screenshots from app stores and product websites. Requires image scraping, storage (Supabase Storage or S3), and frontend rendering.
- **V0 workaround**: No images. All research results are text/markdown.
- **Migration path**: Add image scraping to `scraper.py` or `app_stores.py`. Store images in Supabase Storage. Add image URLs to `ProductProfile` model. Frontend renders images in `ResearchBlock`.
- **When to do it**: After app store scraping is implemented (dependency).

### Quantitative Sentiment Analysis / Scoring — V1
- **What**: Numeric sentiment scores from reviews (Reddit, App Store, Product Hunt) — e.g., "4.2/5 average across 500 reviews", percentage positive/negative, sentiment trends over time.
- **V0 workaround**: Reddit sentiment is qualitative only (LLM-summarized text in `ProductProfile.reddit_sentiment`). No numeric scores.
- **Migration path**: Add review aggregation logic to `explore` pipeline. Add `sentiment_score`, `review_count`, `sentiment_breakdown` fields to `ProductProfile`. Add a sentiment visualization component on the frontend.
- **When to do it**: When review sources (app stores, Product Hunt) are integrated.

### Product Hunt / Hacker News Integration — V1
- **What**: Scrape structured data from Product Hunt (launches, upvotes, comments) and Hacker News (Show HN posts, discussions).
- **V0 workaround**: Web search + Reddit + AlternativeTo cache. These platforms may appear in Serper search results but are not scraped directly.
- **Migration path**: Add dedicated scraper functions for each platform. Add new block types or enrich `ProductProfile` with data from these sources. Use platform APIs where available (Product Hunt has a GraphQL API).
- **When to do it**: When expanding data source coverage for richer competitor profiles.
- **Note**: G2 has been dropped entirely — it requires sign-in and has aggressive anti-scraping measures. AlternativeTo replaces it as the primary curated-alternatives source (pre-seeded in `alternatives_cache` table).

### Full Problem Discovery — V1
- **What**: Quantitative gap scoring (not just LLM qualitative), cross-referencing review sentiment at scale, statistical confidence intervals for market gaps, automated competitor weakness quantification.
- **V0 workaround**: Gap analysis is LLM-qualitative only. Based on competitor profile summaries, not raw review data at scale.
- **Migration path**: After review data sources (G2, app stores) are integrated, run quantitative analysis on aggregated reviews. Add scoring models. Replace qualitative gap_analysis with data-backed gaps.
- **When to do it**: After sentiment analysis and review source integration are complete.

---

## Infrastructure and Ops

### Vercel Migration — V1+
- **What**: Move frontend from Railway to Vercel for better Next.js hosting (ISR, Edge Functions, faster cold starts).
- **V0 workaround**: Both services on Railway.
- **Migration path**: Deploy `frontend/` to Vercel. Change `NEXT_PUBLIC_API_URL` to Railway backend's public URL. Add the Vercel domain to FastAPI's CORS config. Zero code changes.

### Additional Scraping Fallbacks — V1
- **What**: Beyond Jina + BS4 — add Firecrawl, Playwright (headless browser), or ScrapingBee for JS-heavy sites.
- **V0 workaround**: Jina → BS4 fallback. If both fail, skip the product.
- **Migration path**: Add new function in `scraper.py`, add to fallback chain.

### AlternativeTo Seeder Automation — V1
- **What**: Automate the AlternativeTo seed script to run periodically (e.g., monthly cron job) instead of manual one-time execution.
- **V0 workaround**: Manual CLI command: `python -m app.seed_alternatives`. Run once after deployment, then as-needed.
- **Migration path**: Add a cron job on Railway or a scheduled GitHub Action that runs the seed script. Add incremental seeding (only scrape products not in cache or with expired TTL).
- **When to do it**: When the product is live and the alternatives_cache needs regular refreshing.

### Monitoring and Logging — V1
- **What**: Structured logging (JSON logs), error tracking (Sentry), uptime monitoring.
- **V0 workaround**: Print statements and Railway's built-in log viewer.
- **Migration path**: Add `structlog` for backend logging, Sentry SDK for error tracking, Uptime Robot or similar for ping monitoring.

### CI/CD Pipeline — V1
- **What**: Automated tests + deploy on git push.
- **V0 workaround**: Manual deploy via Railway's GitHub integration (auto-deploy on push, but no test step).
- **Migration path**: Add GitHub Actions workflow: run tests → build → deploy. Standard pattern.

### Environment Separation — V1
- **What**: Separate staging and production environments.
- **V0 workaround**: Single environment (production). Test locally before deploying.
- **Migration path**: Duplicate Railway project for staging. Separate Supabase project. Different env vars.

---

## Monetization

### Subscription System (Stripe) — V1
- **What**: Stripe integration for paid tiers (smart, advanced).
- **V0 workaround**: Everything is free.
- **Migration path**: Add Stripe SDK to backend, webhook endpoint for subscription events, `subscriptions` table, tier field on user profile.
- **Dependency**: Requires auth.

### Usage Metering — V1
- **What**: Track and display per-user API usage (researches run, LLM tokens used).
- **V0 workaround**: No tracking.
- **Migration path**: Log each research request with user_id and token count. Add dashboard widget.
- **Dependency**: Requires auth + budget tracking.

### Payment Flow — V1
- **What**: Upgrade/downgrade plans, billing history, invoice downloads.
- **V0 workaround**: None.
- **Migration path**: Stripe Customer Portal handles most of this. Embed via iframe or redirect.
- **Dependency**: Requires Stripe integration.
