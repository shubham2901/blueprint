"""
Single source of truth for all Pydantic models (requests, responses, SSE events, internal types).
Backend types live here; frontend lib/types.ts mirrors these definitions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500, description="User's research query")


class SelectionRequest(BaseModel):
    step_type: str = Field(..., description="'clarify' | 'select_competitors' | 'select_problems'")
    selection: dict = Field(..., description="Selection payload — shape depends on step_type")


class RefineRequest(BaseModel):
    """Request to refine a research step."""
    step_type: str = Field(..., description="Step to refine: 'find_competitors' | 'explore' | 'gap_analysis' | 'define_problem'")
    feedback: Optional[str] = Field(None, description="User feedback on what to improve")


# -----------------------------------------------------------------------------
# Block Models (used in SSE events and LLM responses)
# -----------------------------------------------------------------------------


class ClarificationOption(BaseModel):
    id: str
    label: str
    description: str = ""


class ClarificationQuestion(BaseModel):
    id: str
    label: str
    options: list[ClarificationOption]
    allow_multiple: bool = False
    allow_other: bool = False  # If true, show "Other" option with text input


class ClarificationAnswer(BaseModel):
    """User's answer to a clarification question."""
    question_id: str
    selected_option_ids: list[str]
    other_text: Optional[str] = None  # Free-form text when user selects "Other"


class ResearchBlock(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    title: str
    content: str
    output_data: Optional[dict] = None
    sources: list[str] = []
    cached: bool = False
    cached_at: Optional[datetime] = None


# -----------------------------------------------------------------------------
# LLM Response Models (for structured output validation)
# -----------------------------------------------------------------------------


class CompetitorInfo(BaseModel):
    id: str
    name: str
    description: str
    url: Optional[str] = None
    category: Optional[str] = None
    pricing_model: Optional[str] = None


class CompetitorList(BaseModel):
    competitors: list[CompetitorInfo]
    sources: list[str] = []


class ProductProfile(BaseModel):
    name: str
    content: str
    features_summary: list[str] = []
    pricing_tiers: Optional[str] = None
    target_audience: Optional[str] = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    reddit_sentiment: Optional[str] = None
    sources: list[str] = []


class MarketOverview(BaseModel):
    title: str
    content: str
    sources: list[str] = []


class ProblemArea(BaseModel):
    id: str
    title: str
    description: str
    evidence: list[str] = []
    opportunity_size: Optional[str] = None


class GapAnalysis(BaseModel):
    title: str
    problems: list[ProblemArea]
    sources: list[str] = []


class ProblemStatement(BaseModel):
    title: str
    content: str
    target_user: Optional[str] = None
    key_differentiators: list[str] = []
    validation_questions: list[str] = []


class ClassifyResult(BaseModel):
    intent_type: str
    domain: Optional[str] = None
    quick_response: Optional[str] = None
    clarification_questions: Optional[list[ClarificationQuestion]] = None

    @model_validator(mode="before")
    @classmethod
    def map_text_to_label(cls, data: object) -> object:
        """Map LLM's 'text' field to 'label' on each clarification question."""
        if isinstance(data, dict) and data.get("clarification_questions"):
            for q in data["clarification_questions"]:
                if isinstance(q, dict) and "text" in q and "label" not in q:
                    q["label"] = q.pop("text", "")
        return data


# -----------------------------------------------------------------------------
# SSE Event Models
# -----------------------------------------------------------------------------


class JourneyStartedEvent(BaseModel):
    type: str = "journey_started"
    journey_id: str
    intent_type: str


class QuickResponseEvent(BaseModel):
    type: str = "quick_response"
    message: str


class IntentRedirectEvent(BaseModel):
    type: str = "intent_redirect"
    original_intent: str
    redirected_to: str
    message: str


class StepStartedEvent(BaseModel):
    type: str = "step_started"
    step: str
    label: str


class StepCompletedEvent(BaseModel):
    type: str = "step_completed"
    step: str


class BlockReadyEvent(BaseModel):
    type: str = "block_ready"
    block: ResearchBlock


class BlockErrorEvent(BaseModel):
    type: str = "block_error"
    block_name: str
    error: str
    error_code: str


class ClarificationNeededEvent(BaseModel):
    type: str = "clarification_needed"
    questions: list[ClarificationQuestion]


class WaitingForSelectionEvent(BaseModel):
    type: str = "waiting_for_selection"
    selection_type: str


class ResearchCompleteEvent(BaseModel):
    type: str = "research_complete"
    journey_id: str
    summary: str


class ErrorEvent(BaseModel):
    type: str = "error"
    message: str
    recoverable: bool
    error_code: str


class RefineStartedEvent(BaseModel):
    type: str = "refine_started"
    step_type: str  # Which step is being refined
    message: str


class RefineCompleteEvent(BaseModel):
    type: str = "refine_complete"
    step_type: str


# -----------------------------------------------------------------------------
# Journey Response Models
# -----------------------------------------------------------------------------


class JourneyStepDetail(BaseModel):
    id: str
    step_number: int
    step_type: str
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    user_selection: Optional[dict] = None
    created_at: datetime


class JourneySummary(BaseModel):
    id: str
    title: Optional[str] = None
    status: str
    intent_type: str
    initial_prompt: str
    created_at: datetime
    updated_at: datetime
    step_count: int


class JourneyDetail(BaseModel):
    id: str
    title: Optional[str] = None
    status: str
    intent_type: str
    initial_prompt: str
    steps: list[JourneyStepDetail]
    created_at: datetime
    updated_at: datetime


class JourneyListResponse(BaseModel):
    journeys: list[JourneySummary]


class JourneyDetailResponse(BaseModel):
    journey: JourneyDetail
