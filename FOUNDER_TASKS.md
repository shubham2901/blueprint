# Blueprint — Founder Tasks

Tasks that are on the founder (not the coding agent). These must be completed before or alongside coding. The coding agent will wire functions and schemas — but the actual content below comes from you.

---

## Prompt Writing

These prompts are the brain of the product. The coding agent implements the function signatures in `backend/app/prompts.py` and wires them to the pipeline. You write the actual prompt text.

### 1. ~~Classify Prompt~~ DONE

**Status**: Written and stored in `MODULE_SPEC.md` Section 7 (`build_classify_prompt`).

Covers: intent classification (5 types), domain extraction (with reference hierarchy), multi-question clarification generation, quick responses for small_talk/off_topic. Tonality excluded intentionally — handled by the persona system prompt in `config.py`.

**Schema note**: LLM outputs `text` for question label and options as `{id, label, description}`. The `id` is a stable lowercase slug (e.g., `"mobile"`, `"web"`, `"text-notes"`). Backend maps `text` → `label` post-parse. Selections are tracked by option IDs (e.g., `["mobile", "web"]`), not by label strings.

---

### 2. ~~Gap Analysis Prompt~~ DONE

**Status**: Written and stored in `MODULE_SPEC.md` Section 7 (`build_gap_analysis_prompt`).

**Function**: `build_gap_analysis_prompt(domain: str, profiles: list[dict], clarification_context: dict, market_overview: dict | None = None) -> list[dict]`

Covers: market gap identification (3-6 gaps) from competitor profiles + market overview + user context. Gaps are grounded in profile evidence (features, weaknesses, reddit_sentiment, pricing). Opportunity sizing (high/medium/low). Uses reddit_sentiment from profiles as pre-digested user sentiment — does not fabricate or assume additional customer feedback.

**Signature change note**: Added `domain` (was missing) and `market_overview` (optional, provides market context generated concurrently during the explore step). Updated all callsites in `_run_gap_analysis` and `_run_explore_pipeline`.

---

### 3. ~~Problem Statement Prompt~~ DONE

**Status**: Written and stored in `MODULE_SPEC.md` Section 7 (`build_problem_statement_prompt`).

**Function**: `build_problem_statement_prompt(selected_gaps: list[dict], context: dict) -> list[dict]`

Covers: synthesizing user-selected market gaps into a single actionable problem statement. Outputs: title, content (40-80 word thesis), target_user (persona not demographic), key_differentiators (strategic bets not feature specs), validation_questions (testable assumptions including willingness-to-pay). Grounded in research evidence — no speculation beyond provided data.

---

### 4. ~~Quick Response Templates~~ DONE

**Status**: Written and stored in `MODULE_SPEC.md` Section 7 (`prompts.py` — `SMALL_TALK_RESPONSES`, `OFF_TOPIC_RESPONSES`, `get_quick_response()`).

**Decision**: Hardcoded — cheaper, faster, more predictable. 6 small_talk templates + 4 off_topic templates, randomly selected. The classify prompt still generates `quick_response` via LLM, but the hardcoded templates serve as fallback or full replacement.

---

### 5. Refine Prompt (Review Needed)

**Status**: Initial version written in `backend/app/prompts.py` (`build_refine_prompt`).

**Function**: `build_refine_prompt(original_output: dict, output_schema_name: str, user_feedback: str, additional_context: str = "") -> list[dict]`

Covers: interpreting user feedback patterns (more X, focus on Y, simplify, correct errors), preserving existing good content while addressing feedback, maintaining evidence grounding.

**Review needed**: The initial prompt handles common feedback patterns but you may want to adjust:
- The feedback interpretation guidelines (table in the prompt)
- The quality rules for what should be preserved vs changed
- Any domain-specific refinement behaviors

**Implementation note**: The current refine pipeline (`_refine_competitors`, `_refine_explore`, etc.) appends feedback directly to the original prompts. The dedicated `build_refine_prompt` function is available for a more sophisticated approach where the LLM sees the original output and feedback together. Consider migrating to use `build_refine_prompt` if current refinement quality is insufficient.

**Evaluation tests**: Located in `backend/tests/evals/test_refine_eval.py` with golden test cases in `backend/tests/evals/datasets/refine_cases.json`. Run with:
```bash
cd backend
pytest tests/evals/test_refine_eval.py -v -m eval
```

---

### 6. ~~Persona System Prompt~~ DONE

**Status**: Updated in `MODULE_SPEC.md` Section 1 (`config.py` — `LLM_CONFIG["persona"]["system_prompt"]`) and `ARCHITECTURE.md` Section 2.

**Changes from original draft**:
- Added "for B2C software" scope qualifier
- Added "identify market gaps and define focused problem statements" to capabilities
- Added explicit JSON output instruction ("Output strictly valid JSON when instructed")
- Added domain boundary ("Decline requests for code generation, homework, creative writing, or general knowledge")
- Added balanced analysis guidance ("acknowledge both strengths and weaknesses")
- Added evidence grounding ("Do not speculate beyond what the evidence supports")
- Removed "tonality" field (tone is implicit in the guidelines)

---

## API Keys and Infrastructure

### API Keys to Obtain

| Service | Key Name | Where to Get | Env Var | Priority |
|---------|----------|-------------|---------|----------|
| Gemini | API Key | [Google AI Studio](https://aistudio.google.com/) | `GEMINI_API_KEY` | **Required** |
| Tavily | API Key | [Tavily](https://tavily.com/) | `TAVILY_API_KEY` | **Required** (primary search) |
| Serper | API Key | [Serper.dev](https://serper.dev/) | `SERPER_API_KEY` | Recommended (search fallback) |
| OpenAI | API Key | [OpenAI Platform](https://platform.openai.com/) | `OPENAI_API_KEY` | Recommended (LLM fallback) |
| Anthropic | API Key | [Anthropic Console](https://console.anthropic.com/) | `ANTHROPIC_API_KEY` | Recommended (LLM fallback) |
| Jina | API Key | [Jina AI](https://jina.ai/) | `JINA_API_KEY` | Optional (works without, lower rate) |

**Tavily setup** (primary search):
1. Go to [tavily.com](https://tavily.com/) → create an account
2. Copy the API key from the dashboard
3. Free tier: 1,000 queries/month. Paid plans scale as needed.

**Serper setup** (search fallback):
1. Go to [serper.dev](https://serper.dev/) → create an account
2. Copy the API key from the dashboard
3. Free tier: 2,500 queries/month. Used as fallback when Tavily fails.

### Infrastructure to Set Up

| Service | What to Do | Status |
|---------|-----------|--------|
| Supabase | Create project → get URL + service role key | **DONE** |
| Supabase SQL | Run the schema SQL from `PLAN.md` Part 5 in the SQL editor | Pending (after schema is finalized) |
| Railway | Create project with 2 services (frontend, backend) | **In progress** |
| Railway Env Vars | Configure all env vars from `PLAN.md` Part 7 | Pending (after Railway setup) |
| Domain | Optional: configure custom domain on Railway | Later |

---

## Content and Configuration

### ~~Landing Page Copy~~ DONE

**Status**: Written and stored in `MODULE_SPEC.md` Section 14 (`app/page.tsx`).

- **Heading**: "What would you like to build?"
- **Subheading**: "Describe a product idea or market you're curious about. Blueprint will map the competitive landscape, find gaps, and help you define what to build."
- **Input placeholder**: "e.g., I want to build a note-taking app for students..."

### ~~Suggested Research Pills~~ DONE

**Status**: Written and stored in `MODULE_SPEC.md` Section 14 (`app/page.tsx`).

**Decision**: Pre-fill with placeholder, user clicks RUN. No auto-submit.

| Pill Label | Pre-fills |
|---|---|
| "Build a product" | "I want to build a " |
| "Explore a market" | "Tell me about " |
| "Competitor deep dive" | "Tell me about [product name]" |
| "Find my niche" | "I want to build something in the [space] space" |

### AlternativeTo Seed Script (after backend deployment)

After the backend is deployed and the `alternatives_cache` table exists in Supabase, run the seed script:

```bash
cd backend
python -m app.seed_alternatives
```

This scrapes popular products from `alternativeto.net` and `get.alternative.to` and stores them in the `alternatives_cache` table. Should be run once, then periodically (monthly) to refresh data.

**Expected output**: Summary of how many products and alternatives were seeded per category.

### Supplementary Data Sources (V1 Planning)
Define which forums/platforms to integrate in V1:
- Product Hunt
- Hacker News (Show HN posts, discussions)
- App Store (iOS) — if V0-EXPERIMENTAL scrapers prove unreliable
- Play Store (Android) — if V0-EXPERIMENTAL scrapers prove unreliable
- Others? (Capterra, TrustRadius, etc.)

Note: G2 has been dropped (requires sign-in, aggressive anti-scraping). AlternativeTo replaces it as the primary curated-alternatives source.

---

## Testing and Quality

### Prompt Evaluation Golden Test Cases

The testing framework is set up in `backend/tests/evals/`. Golden test cases are stored in JSON files that you should review and expand:

| File | Purpose | Action Needed |
|------|---------|---------------|
| `datasets/classify_cases.json` | 24 test cases for intent classification | Review edge cases, add domain-specific examples |
| `datasets/competitors_cases.json` | 4 test cases for competitor discovery | Add more domains, verify expected competitors |

**Running prompt evals** (requires real GEMINI_API_KEY):
```bash
cd backend
pytest tests/evals -v -m eval
```

**Adding new test cases**: Each case has `input`, `expected_intent`, `expected_domain`, and `description`. Add cases that cover your specific product domains and edge cases the LLM might mishandle.

### CI/CD Secrets

To enable GitHub Actions CI/CD, add these secrets to your GitHub repository:

| Secret | Required For |
|--------|-------------|
| `GEMINI_API_KEY` | Prompt evaluation tests |
| `SUPABASE_URL` | Integration tests (future) |
| `SUPABASE_SERVICE_KEY` | Integration tests (future) |

**Path**: GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret

### Monitoring Test Results

- **Unit tests**: Run on every commit, no API keys needed
- **Prompt evals**: Run when `prompts.py` changes, nightly, or manual trigger
- **Results**: Check the Actions tab in GitHub for test summaries

---

## Priority Order

1. ~~**Classify prompt**~~ DONE.
2. ~~**API keys**~~ DONE.
3. ~~**Supabase project**~~ DONE.
4. ~~**Gap analysis prompt**~~ DONE.
5. ~~**Problem statement prompt**~~ DONE.
6. ~~**Quick response templates**~~ DONE.
7. ~~**Persona system prompt**~~ DONE.
8. ~~**Landing page copy + pills**~~ DONE.
9. **Railway setup** — in progress.
10. **Run Supabase SQL schema** — after schema finalized, before backend testing.
11. **Railway env vars** — after Railway setup.
12. **Run AlternativeTo seed script** — after backend deployment + Supabase schema setup.
