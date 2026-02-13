"""
Blueprint Backend — Research API (POST /api/research, POST /api/research/{id}/selection)

Core SSE streaming endpoints that orchestrate the entire research pipeline.
"""

import asyncio
import json
import time
from dataclasses import asdict
from hashlib import sha256

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app import db, llm, prompts, scraper, search
from app.config import generate_error_code, log
from app.llm import LLMError, LLMValidationError
from app.models import (
    BlockErrorEvent,
    BlockReadyEvent,
    ClarificationNeededEvent,
    ClassifyResult,
    CompetitorList,
    ErrorEvent,
    GapAnalysis,
    IntentRedirectEvent,
    JourneyStartedEvent,
    MarketOverview,
    ProblemStatement,
    ProductProfile,
    QuickResponseEvent,
    ResearchBlock,
    ResearchCompleteEvent,
    ResearchRequest,
    SelectionRequest,
    StepCompletedEvent,
    StepStartedEvent,
    WaitingForSelectionEvent,
)
from app.scraper import ScraperError

router = APIRouter(prefix="/api/research", tags=["research"])

# In-memory dedup tracker (single-instance assumption)
_active_researches: dict[str, bool] = {}


def _make_dedup_key(journey_id: str | None, prompt: str | None) -> str:
    """
    Generate a deduplication key.
    - If journey_id is provided: use journey_id
    - If not: use sha256 hash of the prompt
    """
    if journey_id:
        return f"journey:{journey_id}"
    return f"prompt:{sha256((prompt or '').encode()).hexdigest()[:16]}"


def _format_sse_event(event_data: dict) -> str:
    """Format a dict as an SSE event string. Format: 'data: {json}\\n\\n'"""
    return f"data: {json.dumps(event_data)}\n\n"


def _serialize_event(event) -> str:
    """Serialize a Pydantic event model to SSE string."""
    return _format_sse_event(event.model_dump())


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post("")
async def start_research(request: ResearchRequest) -> StreamingResponse:
    """
    POST /api/research

    Classify intent and start a new research session.
    Returns SSE stream.
    """
    prompt = request.prompt.strip()
    dedup_key = _make_dedup_key(None, prompt)

    if dedup_key in _active_researches:
        raise HTTPException(status_code=409, detail="Research already in progress for this prompt")

    _active_researches[dedup_key] = True

    async def stream():
        try:
            async for chunk in _run_classify_pipeline(prompt):
                yield chunk
        finally:
            _active_researches.pop(dedup_key, None)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{journey_id}/selection")
async def submit_selection(journey_id: str, request: SelectionRequest) -> StreamingResponse:
    """
    POST /api/research/{journey_id}/selection

    Submit a user selection and continue the research pipeline.
    Returns 404 if journey not found, 409 if research already in progress.
    """
    journey = await db.get_journey(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    dedup_key = _make_dedup_key(journey_id, None)
    if dedup_key in _active_researches:
        raise HTTPException(status_code=409, detail="Research already in progress for this journey")

    _active_researches[dedup_key] = True

    step_type = request.step_type
    selection = request.selection

    async def stream():
        try:
            if step_type == "clarify":
                async for chunk in _run_competitor_pipeline(journey_id, selection, journey):
                    yield chunk
            elif step_type == "select_competitors":
                async for chunk in _run_explore_pipeline(journey_id, selection, journey):
                    yield chunk
            elif step_type == "select_problems":
                async for chunk in _run_problem_pipeline(journey_id, selection, journey):
                    yield chunk
            else:
                code = generate_error_code()
                log("ERROR", "invalid step_type", journey_id=journey_id, step_type=step_type, error_code=code)
                evt = ErrorEvent(
                    message="Invalid selection step type.",
                    recoverable=False,
                    error_code=code,
                )
                yield _serialize_event(evt)
        finally:
            _active_researches.pop(dedup_key, None)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -----------------------------------------------------------------------------
# Pipeline: Classify
# -----------------------------------------------------------------------------


async def _run_classify_pipeline(prompt: str):
    """Async generator yielding SSE events for classify + clarify phase."""
    start_ms = time.perf_counter()
    log("INFO", "pipeline started", pipeline="classify", prompt=prompt[:50])

    try:
        evt = StepStartedEvent(step="classifying", label="Understanding your query")
        yield _serialize_event(evt)
        log("INFO", "sse event sent", event_type="step_started", step_type="classify")

        classify_result: ClassifyResult = await llm.call_llm_structured(
            prompts.build_classify_prompt(prompt),
            ClassifyResult,
            journey_id=None,
        )

        evt = StepCompletedEvent(step="classifying")
        yield _serialize_event(evt)
        log("INFO", "sse event sent", event_type="step_completed", step_type="classify")

        intent_type = classify_result.intent_type

        if intent_type in ("small_talk", "off_topic"):
            msg = classify_result.quick_response or (
                "I'm Blueprint, a product research assistant. What would you like to explore?"
            )
            evt = QuickResponseEvent(message=msg)
            yield _serialize_event(evt)
            log("INFO", "pipeline completed", pipeline="classify", intent=intent_type, duration_ms=int((time.perf_counter() - start_ms) * 1000))
            return

        if intent_type == "improve":
            intent_type = "explore"

        journey_id = await db.create_journey(prompt, intent_type)
        if not journey_id:
            code = generate_error_code()
            log("ERROR", "db write failed", operation="create_journey", error_code=code)
            evt = ErrorEvent(
                message="Something went wrong saving your research. Please try again.",
                recoverable=False,
                error_code=code,
            )
            yield _serialize_event(evt)
            return

        evt = JourneyStartedEvent(journey_id=journey_id, intent_type=intent_type)
        yield _serialize_event(evt)
        log("INFO", "sse event sent", journey_id=journey_id, event_type="journey_started")

        if classify_result.intent_type == "improve":
            evt = IntentRedirectEvent(
                original_intent="improve",
                redirected_to="explore",
                message="Improve flow coming soon. Starting an explore session for your product.",
            )
            yield _serialize_event(evt)

        output_data = {
            "intent_type": intent_type,
            "domain": classify_result.domain,
            "clarification_questions": (
                [q.model_dump() for q in classify_result.clarification_questions]
                if classify_result.clarification_questions
                else None
            ),
        }
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=1,
            step_type="classify",
            input_data={"prompt": prompt},
            output_data=output_data,
        )

        if classify_result.clarification_questions:
            evt = ClarificationNeededEvent(questions=classify_result.clarification_questions)
            yield _serialize_event(evt)
            log("INFO", "sse event sent", journey_id=journey_id, event_type="clarification_needed")

        evt = WaitingForSelectionEvent(selection_type="clarification")
        yield _serialize_event(evt)
        log("INFO", "sse event sent", journey_id=journey_id, event_type="waiting_for_selection", selection_type="clarification")

        log("INFO", "pipeline completed", journey_id=journey_id, pipeline="classify", duration_ms=int((time.perf_counter() - start_ms) * 1000))

    except (LLMError, LLMValidationError) as e:
        code = generate_error_code()
        log("ERROR", "sse error event sent", error_code=code, error=str(e), recoverable=False)
        evt = ErrorEvent(
            message="We're having trouble generating results right now. Please try again in a moment.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "pipeline error", pipeline="classify", error=str(e), error_code=code)
        evt = ErrorEvent(
            message="Something unexpected happened. Please try again.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)


# -----------------------------------------------------------------------------
# Pipeline: Competitor
# -----------------------------------------------------------------------------


async def _run_competitor_pipeline(journey_id: str, selection: dict, journey: dict):
    """Async generator yielding SSE events for competitor finding phase."""
    start_ms = time.perf_counter()
    log("INFO", "pipeline started", journey_id=journey_id, pipeline="competitor")

    try:
        steps = journey.get("steps", [])
        classify_step = next((s for s in steps if s.get("step_type") == "classify"), None)
        domain = (classify_step or {}).get("output_data", {}).get("domain") or ""

        clarification_context = {}
        for ans in selection.get("answers", []):
            qid = ans.get("question_id")
            opts = ans.get("selected_option_ids", [])
            if qid:
                clarification_context[qid] = opts

        step_num = await db.get_next_step_number(journey_id)
        questions_presented = (classify_step or {}).get("output_data", {}).get("clarification_questions") or []
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=step_num,
            step_type="clarify",
            input_data={"questions_presented": questions_presented},
            user_selection=selection,
        )

        evt = StepStartedEvent(step="finding_competitors", label="Finding competitors")
        yield _serialize_event(evt)
        log("INFO", "sse event sent", journey_id=journey_id, event_type="step_started", step_type="find_competitors")

        ctx_parts = []
        for k, v in clarification_context.items():
            if isinstance(v, list):
                ctx_parts.extend(str(x) for x in v)
            else:
                ctx_parts.append(str(v))
        context_str = " ".join(ctx_parts) if ctx_parts else ""
        search_query = f"{domain} {context_str} competitors".strip()

        norm_domain = db.normalize_product_name(domain or "general")
        alternatives_task = db.get_cached_alternatives(norm_domain)
        search_task = search.search(search_query, num_results=10)
        reddit_task = search.search_reddit(f"{domain} {context_str}", num_results=5)

        alternatives_data, search_results, reddit_results = await asyncio.gather(
            alternatives_task,
            search_task,
            reddit_task,
        )

        search_results_dict = [asdict(r) for r in search_results] if search_results else []
        reddit_results_dict = [asdict(r) for r in reddit_results] if reddit_results else []

        competitors_prompt = prompts.build_competitors_prompt(
            domain=domain,
            clarification_context=clarification_context,
            alternatives_data=alternatives_data,
            app_store_results=None,
            search_results=search_results_dict,
            reddit_results=reddit_results_dict,
        )
        competitors: CompetitorList = await llm.call_llm_structured(
            competitors_prompt,
            CompetitorList,
            journey_id=journey_id,
        )

        sources = list(set((c.url for c in competitors.competitors if c.url) or []))[:10]
        block = ResearchBlock(
            type="competitor_list",
            title="Competitors",
            content="\n\n".join(f"**{c.name}**: {c.description}" for c in competitors.competitors),
            output_data={"competitors": [c.model_dump() for c in competitors.competitors]},
            sources=sources,
        )

        step_num = await db.get_next_step_number(journey_id)
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=step_num,
            step_type="find_competitors",
            input_data={
                "domain": domain,
                "clarification_context": clarification_context,
                "search_query": search_query,
            },
            output_data={"competitors": [c.model_dump() for c in competitors.competitors], "sources": sources},
        )

        evt = BlockReadyEvent(block=block)
        yield _serialize_event(evt)
        log("INFO", "sse event sent", journey_id=journey_id, event_type="block_ready", block_type="competitor_list")

        evt = StepCompletedEvent(step="finding_competitors")
        yield _serialize_event(evt)

        evt = WaitingForSelectionEvent(selection_type="competitors")
        yield _serialize_event(evt)

        log("INFO", "pipeline completed", journey_id=journey_id, pipeline="competitor", duration_ms=int((time.perf_counter() - start_ms) * 1000))

    except (LLMError, LLMValidationError) as e:
        code = generate_error_code()
        log("ERROR", "sse error event sent", journey_id=journey_id, error_code=code, error=str(e), recoverable=False)
        evt = ErrorEvent(
            message="We're having trouble generating results right now. Please try again in a moment.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "pipeline error", journey_id=journey_id, pipeline="competitor", error=str(e), error_code=code)
        evt = ErrorEvent(
            message="Something unexpected happened. Please try again.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)


# -----------------------------------------------------------------------------
# Pipeline: Explore
# -----------------------------------------------------------------------------


async def _run_explore_pipeline(journey_id: str, selection: dict, journey: dict):
    """Async generator yielding SSE events for explore phase."""
    start_ms = time.perf_counter()
    intent_type = journey.get("intent_type", "explore")
    log("INFO", "pipeline started", journey_id=journey_id, pipeline="explore", intent=intent_type)

    try:
        log("INFO", "explore: extracting steps", journey_id=journey_id)
        steps = journey.get("steps", [])
        find_comp_step = next((s for s in steps if s.get("step_type") == "find_competitors"), None)
        classify_step = next((s for s in steps if s.get("step_type") == "classify"), None)

        domain = (classify_step or {}).get("output_data", {}).get("domain") or ""
        competitors_presented = (find_comp_step or {}).get("output_data", {}).get("competitors") or []
        log("INFO", "explore: found competitors", journey_id=journey_id, count=len(competitors_presented))

        selected_ids = selection.get("competitor_ids", []) or selection.get("selected_competitor_ids", [])
        selected_competitors = [c for c in competitors_presented if c.get("id") in selected_ids]
        log("INFO", "explore: selected competitors", journey_id=journey_id, selected_count=len(selected_competitors))

        log("INFO", "explore: getting next step number", journey_id=journey_id)
        step_num = await db.get_next_step_number(journey_id)
        log("INFO", "explore: saving journey step", journey_id=journey_id, step_num=step_num)
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=step_num,
            step_type="select_competitors",
            input_data={"competitors_presented": [{"id": c.get("id"), "name": c.get("name")} for c in competitors_presented]},
            user_selection=selection,
        )
        log("INFO", "explore: journey step saved", journey_id=journey_id)

        evt = StepStartedEvent(step="exploring", label="Analyzing products")
        yield _serialize_event(evt)
        log("INFO", "sse event sent", journey_id=journey_id, event_type="step_started", step_type="explore")

        clarification_context = {}
        clarify_step = next((s for s in steps if s.get("step_type") == "clarify"), None)
        if clarify_step and clarify_step.get("user_selection", {}).get("answers"):
            for ans in clarify_step["user_selection"]["answers"]:
                qid = ans.get("question_id")
                opts = ans.get("selected_option_ids", [])
                if qid:
                    clarification_context[qid] = opts

        profiles: list[dict] = []
        market_overview_dict: dict | None = None

        async def process_competitor(comp: dict):
            name = comp.get("name", "")
            url = comp.get("url", "")
            norm_name = db.normalize_product_name(name)

            cached = await db.get_cached_product(norm_name)
            if cached:
                prof = {
                    "name": cached.get("name", name),
                    "content": cached.get("description", ""),
                    "features_summary": cached.get("features_summary") or [],
                    "pricing_tiers": cached.get("pricing_model"),
                    "target_audience": cached.get("category"),
                    "strengths": cached.get("strengths") or [],
                    "weaknesses": cached.get("weaknesses") or [],
                    "reddit_sentiment": None,
                    "sources": cached.get("sources") or [],
                    "cached": True,
                    "cached_at": cached.get("last_scraped_at"),
                }
                return ("profile", prof, None)

            scraped = ""
            reddit_content = ""

            try:
                if url:
                    scraped = await scraper.scrape(url)
            except ScraperError:
                pass

            try:
                reddit_results = await search.search_reddit(f"{name} review", num_results=5)
                reddit_content = "\n\n".join(r.snippet for r in reddit_results) if reddit_results else ""
            except Exception:
                pass

            try:
                explore_prompt = prompts.build_explore_prompt(name, scraped, reddit_content)
                profile: ProductProfile = await llm.call_llm_structured(
                    explore_prompt,
                    ProductProfile,
                    journey_id=journey_id,
                )
                prof_dict = profile.model_dump()
                prof_dict["cached"] = False
                prof_dict["cached_at"] = None

                await db.store_product({
                    "normalized_name": norm_name,
                    "name": prof_dict.get("name", name),
                    "url": url or None,
                    "description": (prof_dict.get("content", ""))[:50000],
                    "category": prof_dict.get("target_audience"),
                    "pricing_model": prof_dict.get("pricing_tiers"),
                    "features_summary": prof_dict.get("features_summary", []),
                    "strengths": prof_dict.get("strengths", []),
                    "weaknesses": prof_dict.get("weaknesses", []),
                    "sources": prof_dict.get("sources", []),
                })

                return ("profile", prof_dict, None)
            except Exception as e:
                return ("error", name, str(e))

        tasks = [process_competitor(c) for c in selected_competitors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                code = generate_error_code()
                evt = BlockErrorEvent(block_name="Unknown", error=str(r), error_code=code)
                yield _serialize_event(evt)
                continue
            kind, data, err = r
            if kind == "error":
                code = generate_error_code()
                evt = BlockErrorEvent(
                    block_name=data,
                    error="We couldn't access this product's website. Other results are still available.",
                    error_code=code,
                )
                yield _serialize_event(evt)
            else:
                profiles.append(data)
                block = ResearchBlock(
                    type="product_profile",
                    title=data.get("name", "Product"),
                    content=data.get("content", ""),
                    output_data={"profile": data},
                    sources=data.get("sources", []),
                    cached=data.get("cached", False),
                    cached_at=data.get("cached_at"),
                )
                evt = BlockReadyEvent(block=block)
                yield _serialize_event(evt)

        try:
            overview_prompt = prompts.build_market_overview_prompt(domain, profiles)
            market_overview: MarketOverview = await llm.call_llm_structured(
                overview_prompt,
                MarketOverview,
                journey_id=journey_id,
            )
            market_overview_dict = market_overview.model_dump()
            block = ResearchBlock(
                type="market_overview",
                title=market_overview_dict.get("title", "Market Overview"),
                content=market_overview_dict.get("content", ""),
                output_data={"overview": market_overview_dict},
                sources=market_overview_dict.get("sources", []),
            )
            evt = BlockReadyEvent(block=block)
            yield _serialize_event(evt)
        except Exception as e:
            code = generate_error_code()
            evt = BlockErrorEvent(
                block_name="Market Overview",
                error="We couldn't generate the market overview. Other results are still available.",
                error_code=code,
            )
            yield _serialize_event(evt)

        evt = StepCompletedEvent(step="exploring")
        yield _serialize_event(evt)

        if intent_type == "build":
            async for chunk in _run_gap_analysis(
                journey_id, domain, profiles, clarification_context, market_overview_dict
            ):
                yield chunk

            evt = WaitingForSelectionEvent(selection_type="problems")
            yield _serialize_event(evt)
        else:
            step_num = await db.get_next_step_number(journey_id)
            await db.save_journey_step(
                journey_id=journey_id,
                step_number=step_num,
                step_type="explore",
                input_data={"products_to_explore": [p.get("name") for p in profiles], "domain": domain},
                output_data={"product_profiles": profiles, "market_overview": market_overview_dict},
            )
            await db.update_journey_status(journey_id, "completed")
            evt = ResearchCompleteEvent(journey_id=journey_id, summary="Research complete")
            yield _serialize_event(evt)

        log("INFO", "pipeline completed", journey_id=journey_id, pipeline="explore", duration_ms=int((time.perf_counter() - start_ms) * 1000))

    except (LLMError, LLMValidationError) as e:
        code = generate_error_code()
        log("ERROR", "sse error event sent", journey_id=journey_id, error_code=code, error=str(e), recoverable=False)
        evt = ErrorEvent(
            message="We're having trouble generating results right now. Please try again in a moment.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "pipeline error", journey_id=journey_id, pipeline="explore", error=str(e), error_code=code)
        evt = ErrorEvent(
            message="Something unexpected happened. Please try again.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)


# -----------------------------------------------------------------------------
# Pipeline: Gap Analysis
# -----------------------------------------------------------------------------


async def _run_gap_analysis(
    journey_id: str,
    domain: str,
    profiles: list[dict],
    clarification_context: dict,
    market_overview: dict | None = None,
):
    """Async generator yielding SSE events for gap analysis (build intent only)."""
    log("INFO", "pipeline started", journey_id=journey_id, pipeline="gap_analysis")

    try:
        evt = StepStartedEvent(step="gap_analyzing", label="Finding market gaps")
        yield _serialize_event(evt)

        gap_prompt = prompts.build_gap_analysis_prompt(
            domain, profiles, clarification_context, market_overview
        )
        gap: GapAnalysis = await llm.call_llm_structured(
            gap_prompt,
            GapAnalysis,
            journey_id=journey_id,
        )

        block = ResearchBlock(
            type="gap_analysis",
            title=gap.title,
            content="\n\n".join(f"**{p.title}**: {p.description}" for p in gap.problems),
            output_data={"problems": [p.model_dump() for p in gap.problems]},
            sources=gap.sources,
        )

        step_num = await db.get_next_step_number(journey_id)
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=step_num,
            step_type="explore",
            input_data={"profiles": profiles, "domain": domain},
            output_data={"gap_analysis": gap.model_dump(), "product_profiles": profiles},
        )

        evt = BlockReadyEvent(block=block)
        yield _serialize_event(evt)

        evt = StepCompletedEvent(step="gap_analyzing")
        yield _serialize_event(evt)

    except Exception as e:
        code = generate_error_code()
        log("ERROR", "gap analysis failed", journey_id=journey_id, error=str(e), error_code=code)
        evt = BlockErrorEvent(
            block_name="Gap Analysis",
            error="We couldn't identify market gaps. Other results are still available.",
            error_code=code,
        )
        yield _serialize_event(evt)


# -----------------------------------------------------------------------------
# Pipeline: Problem Statement
# -----------------------------------------------------------------------------


async def _run_problem_pipeline(journey_id: str, selection: dict, journey: dict):
    """Async generator yielding SSE events for problem statement (build intent only)."""
    start_ms = time.perf_counter()
    log("INFO", "pipeline started", journey_id=journey_id, pipeline="problem")

    try:
        steps = journey.get("steps", [])
        explore_step = next((s for s in steps if s.get("step_type") == "explore"), None)
        gap_data = (explore_step or {}).get("output_data", {}).get("gap_analysis", {})
        problems_presented = gap_data.get("problems", [])
        classify_step = next((s for s in steps if s.get("step_type") == "classify"), None)
        clarify_step = next((s for s in steps if s.get("step_type") == "clarify"), None)

        selected_ids = selection.get("problem_ids", []) or selection.get("selected_problem_ids", [])
        selected_problems = [p for p in problems_presented if p.get("id") in selected_ids]

        domain = (classify_step or {}).get("output_data", {}).get("domain") or ""
        competitors = []
        for s in steps:
            od = s.get("output_data", {}) or {}
            if "competitors" in od:
                competitors = [c.get("name") for c in od["competitors"] if c.get("name")]
                break
        clarification_context = (clarify_step or {}).get("user_selection", {}) or {}
        if isinstance(clarification_context, dict) and "answers" in clarification_context:
            ctx = {}
            for a in clarification_context.get("answers", []):
                qid = a.get("question_id")
                if qid:
                    ctx[qid] = a.get("selected_option_ids", [])
            clarification_context = ctx
        elif not isinstance(clarification_context, dict):
            clarification_context = {}

        step_num = await db.get_next_step_number(journey_id)
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=step_num,
            step_type="select_problems",
            input_data={"problems_presented": [{"id": p.get("id"), "title": p.get("title")} for p in problems_presented]},
            user_selection=selection,
        )

        evt = StepStartedEvent(step="defining_problem", label="Defining your problem")
        yield _serialize_event(evt)

        context = {
            "domain": domain,
            "competitors_analyzed": competitors,
            "clarification_context": clarification_context,
        }
        problem_prompt = prompts.build_problem_statement_prompt(selected_problems, context)
        statement: ProblemStatement = await llm.call_llm_structured(
            problem_prompt,
            ProblemStatement,
            journey_id=journey_id,
        )

        block = ResearchBlock(
            type="problem_statement",
            title=statement.title,
            content=statement.content,
            output_data={"statement": statement.model_dump()},
            sources=[],
        )

        step_num = await db.get_next_step_number(journey_id)
        await db.save_journey_step(
            journey_id=journey_id,
            step_number=step_num,
            step_type="define_problem",
            input_data={"selected_problems": selected_problems, "competitor_context": context},
            output_data={"problem_statement": statement.model_dump()},
        )

        evt = BlockReadyEvent(block=block)
        yield _serialize_event(evt)

        evt = StepCompletedEvent(step="defining_problem")
        yield _serialize_event(evt)

        await db.update_journey_status(journey_id, "completed")

        evt = ResearchCompleteEvent(journey_id=journey_id, summary="Research complete")
        yield _serialize_event(evt)

        log("INFO", "pipeline completed", journey_id=journey_id, pipeline="problem", duration_ms=int((time.perf_counter() - start_ms) * 1000))

    except (LLMError, LLMValidationError) as e:
        code = generate_error_code()
        log("ERROR", "sse error event sent", journey_id=journey_id, error_code=code, error=str(e), recoverable=False)
        evt = ErrorEvent(
            message="We're having trouble generating results right now. Please try again in a moment.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)
    except Exception as e:
        code = generate_error_code()
        log("ERROR", "pipeline error", journey_id=journey_id, pipeline="problem", error=str(e), error_code=code)
        evt = ErrorEvent(
            message="Something unexpected happened. Please try again.",
            recoverable=False,
            error_code=code,
        )
        yield _serialize_event(evt)
