"""
Blueprint Backend — Refine Prompt Evaluation Tests

Tests for evaluating the quality of the refine prompt using real LLM calls.
These tests verify that the LLM can correctly interpret user feedback and
improve previous outputs accordingly.

Run with: pytest tests/evals/test_refine_eval.py -v -m eval
"""

import json
import pytest

from app.prompts import build_refine_prompt


pytestmark = [pytest.mark.eval, pytest.mark.slow]


# -----------------------------------------------------------------------------
# Basic Refinement Tests
# -----------------------------------------------------------------------------


class TestRefinePromptBasics:
    """Basic tests for refine prompt functionality."""

    @pytest.mark.asyncio
    async def test_refine_returns_valid_json(self, check_api_keys, real_llm_call):
        """Test that refine prompt returns valid JSON matching the schema."""
        from pydantic import BaseModel
        from typing import Optional
        
        class SimpleOutput(BaseModel):
            """Simple test output schema."""
            items: list[str]
            count: int
            note: Optional[str] = None
        
        original = {"items": ["item1", "item2"], "count": 2, "note": None}
        messages = build_refine_prompt(
            original_output=original,
            output_schema_name="SimpleOutput",
            user_feedback="Add one more item",
        )
        
        result = await real_llm_call(messages, SimpleOutput)
        
        assert isinstance(result, SimpleOutput)
        assert len(result.items) >= 2  # Should preserve original items
        assert result.count == len(result.items)  # Count should match

    @pytest.mark.asyncio
    async def test_refine_preserves_existing_content(self, check_api_keys, real_llm_call):
        """Test that refinement preserves good existing content."""
        from pydantic import BaseModel
        
        class CompetitorList(BaseModel):
            """Simplified competitor list for testing."""
            competitors: list[dict]
        
        original = {
            "competitors": [
                {"id": "1", "name": "Notion", "description": "All-in-one workspace"},
                {"id": "2", "name": "Obsidian", "description": "Local-first notes"},
            ]
        }
        
        messages = build_refine_prompt(
            original_output=original,
            output_schema_name="CompetitorList",
            user_feedback="Add Roam Research to the list",
        )
        
        result = await real_llm_call(messages, CompetitorList)
        
        # Original competitors should still be present
        names = [c.get("name", "").lower() for c in result.competitors]
        assert "notion" in names or any("notion" in n for n in names)
        assert "obsidian" in names or any("obsidian" in n for n in names)
        # New competitor should be added
        assert len(result.competitors) >= 3

    @pytest.mark.asyncio
    async def test_refine_handles_correction_feedback(self, check_api_keys, real_llm_call):
        """Test that refinement corrects errors when pointed out."""
        from pydantic import BaseModel
        from typing import Optional
        
        class ProductProfile(BaseModel):
            """Simplified product profile for testing."""
            name: str
            pricing: str
            has_mobile_app: bool
            features: list[str]
        
        # Intentionally incorrect information
        original = {
            "name": "Obsidian",
            "pricing": "$10/month subscription required",
            "has_mobile_app": False,
            "features": ["Markdown editing", "Linking"],
        }
        
        messages = build_refine_prompt(
            original_output=original,
            output_schema_name="ProductProfile",
            user_feedback="This is wrong - Obsidian is free for personal use and has mobile apps",
        )
        
        result = await real_llm_call(messages, ProductProfile)
        
        # Should correct the errors
        assert "free" in result.pricing.lower() or "$0" in result.pricing or "no cost" in result.pricing.lower()
        assert result.has_mobile_app is True


# -----------------------------------------------------------------------------
# Feedback Pattern Tests
# -----------------------------------------------------------------------------


class TestFeedbackPatterns:
    """Tests for specific feedback patterns the refine prompt should handle."""

    @pytest.mark.asyncio
    async def test_more_x_pattern(self, check_api_keys, real_llm_call):
        """Test 'more X' feedback pattern adds more items."""
        from pydantic import BaseModel
        
        class GapAnalysis(BaseModel):
            """Simplified gap analysis for testing."""
            problems: list[dict]
        
        original = {
            "problems": [
                {"id": "1", "title": "Mobile UX gap", "description": "Poor mobile experience"}
            ]
        }
        
        messages = build_refine_prompt(
            original_output=original,
            output_schema_name="GapAnalysis",
            user_feedback="Add more gaps - what about pricing and collaboration?",
            additional_context="Domain: Note-taking apps",
        )
        
        result = await real_llm_call(messages, GapAnalysis)
        
        assert len(result.problems) >= 2  # Should have added more
        titles_lower = " ".join([p.get("title", "").lower() for p in result.problems])
        # Should mention at least one of the requested topics
        assert "pricing" in titles_lower or "collaborat" in titles_lower or len(result.problems) >= 3

    @pytest.mark.asyncio
    async def test_focus_on_y_pattern(self, check_api_keys, real_llm_call):
        """Test 'focus on Y' feedback pattern narrows content."""
        from pydantic import BaseModel
        
        class CompetitorList(BaseModel):
            """Simplified competitor list for testing."""
            competitors: list[dict]
            focus_area: str = ""
        
        original = {
            "competitors": [
                {"id": "1", "name": "Notion", "platform": "web, mobile, desktop"},
                {"id": "2", "name": "Bear", "platform": "iOS, macOS"},
                {"id": "3", "name": "Roam", "platform": "web"},
                {"id": "4", "name": "Apple Notes", "platform": "iOS, macOS"},
            ],
            "focus_area": "general note-taking",
        }
        
        messages = build_refine_prompt(
            original_output=original,
            output_schema_name="CompetitorList",
            user_feedback="Focus only on iOS-native apps",
        )
        
        result = await real_llm_call(messages, CompetitorList)
        
        # Should emphasize iOS apps
        ios_keywords = ["ios", "iphone", "apple", "bear"]
        competitors_str = json.dumps(result.competitors).lower()
        assert any(kw in competitors_str for kw in ios_keywords)

    @pytest.mark.asyncio
    async def test_simplify_pattern(self, check_api_keys, real_llm_call):
        """Test 'simpler' feedback pattern reduces complexity."""
        from pydantic import BaseModel
        from typing import Optional
        
        class ProblemStatement(BaseModel):
            """Simplified problem statement for testing."""
            title: str
            content: str
            key_differentiators: list[str]
        
        original = {
            "title": "Comprehensive Mobile-First Privacy-Preserving Knowledge Management Platform for Enterprise Knowledge Workers",
            "content": (
                "Professional knowledge workers in enterprise environments need a mobile-first, "
                "privacy-preserving knowledge management solution that combines the organizational power "
                "of desktop tools with the speed of mobile capture, while maintaining end-to-end encryption, "
                "offline-first architecture, and seamless cross-platform synchronization."
            ),
            "key_differentiators": [
                "Mobile-first architecture",
                "End-to-end encryption",
                "Offline-first with conflict-free sync",
                "AI-assisted organization",
                "Enterprise SSO integration",
                "Cross-platform parity",
            ],
        }
        
        messages = build_refine_prompt(
            original_output=original,
            output_schema_name="ProblemStatement",
            user_feedback="Too complex. Simplify to focus on just mobile capture.",
        )
        
        result = await real_llm_call(messages, ProblemStatement)
        
        # Title should be shorter
        assert len(result.title) < len(original["title"])
        # Should have fewer differentiators
        assert len(result.key_differentiators) <= len(original["key_differentiators"])
        # Should focus on mobile
        combined_text = (result.title + result.content).lower()
        assert "mobile" in combined_text


# -----------------------------------------------------------------------------
# Golden Test Case Evaluation
# -----------------------------------------------------------------------------


class TestRefineGoldenCases:
    """Tests using golden test cases from datasets/refine_cases.json."""

    @pytest.mark.asyncio
    async def test_competitors_add_more(self, check_api_keys, real_llm_call, refine_test_cases):
        """Test adding more competitors to an existing list."""
        from pydantic import BaseModel
        
        class CompetitorList(BaseModel):
            competitors: list[dict]
            sources: list[str] = []
        
        case = next(c for c in refine_test_cases if c["id"] == "competitors-add-more")
        
        messages = build_refine_prompt(
            original_output=case["original_output"],
            output_schema_name=case["output_schema_name"],
            user_feedback=case["user_feedback"],
            additional_context=case.get("additional_context", ""),
        )
        
        result = await real_llm_call(messages, CompetitorList)
        
        # Should have at least the minimum expected competitors
        assert len(result.competitors) >= case.get("min_competitors", 3)
        # Should preserve original competitors
        original_names = {c["name"].lower() for c in case["original_output"]["competitors"]}
        result_names = {c.get("name", "").lower() for c in result.competitors}
        assert original_names.issubset(result_names) or len(result.competitors) >= case["min_competitors"]

    @pytest.mark.asyncio
    async def test_gap_analysis_more_detail(self, check_api_keys, real_llm_call, refine_test_cases):
        """Test expanding detail on a specific gap."""
        from pydantic import BaseModel
        
        class GapAnalysis(BaseModel):
            problems: list[dict]
        
        case = next(c for c in refine_test_cases if c["id"] == "gap-analysis-more-detail")
        
        messages = build_refine_prompt(
            original_output=case["original_output"],
            output_schema_name=case["output_schema_name"],
            user_feedback=case["user_feedback"],
            additional_context=case.get("additional_context", ""),
        )
        
        result = await real_llm_call(messages, GapAnalysis)
        
        # Find the focused gap
        focus_id = case.get("focus_gap_id", "gap-1")
        focused_gap = next((p for p in result.problems if p.get("id") == focus_id), None)
        
        if focused_gap:
            # Should have more evidence
            original_gap = next(p for p in case["original_output"]["problems"] if p.get("id") == focus_id)
            assert len(focused_gap.get("evidence", [])) >= len(original_gap.get("evidence", []))

    @pytest.mark.asyncio
    async def test_problem_statement_simplify(self, check_api_keys, real_llm_call, refine_test_cases):
        """Test simplifying a complex problem statement."""
        from pydantic import BaseModel
        from typing import Optional
        
        class ProblemStatement(BaseModel):
            title: str
            content: str
            target_user: Optional[str] = None
            key_differentiators: list[str] = []
            validation_questions: list[str] = []
        
        case = next(c for c in refine_test_cases if c["id"] == "problem-statement-simplify")
        
        messages = build_refine_prompt(
            original_output=case["original_output"],
            output_schema_name=case["output_schema_name"],
            user_feedback=case["user_feedback"],
            additional_context=case.get("additional_context", ""),
        )
        
        result = await real_llm_call(messages, ProblemStatement)
        
        # Should be simpler (shorter title and content, fewer differentiators)
        original = case["original_output"]
        assert (
            len(result.title) <= len(original["title"]) or
            len(result.key_differentiators) <= len(original["key_differentiators"])
        )
        # Should focus on mobile capture
        combined = (result.title + " " + result.content).lower()
        assert "mobile" in combined or "capture" in combined


# -----------------------------------------------------------------------------
# DeepEval Metric Tests
# -----------------------------------------------------------------------------


class TestRefineWithMetrics:
    """Tests using DeepEval metrics for evaluation."""

    @pytest.mark.asyncio
    async def test_refinement_quality_score(
        self,
        check_api_keys,
        real_llm_call,
        refine_test_cases,
        refinement_quality_metric,
    ):
        """Test overall refinement quality using DeepEval metric."""
        try:
            from deepeval.test_case import LLMTestCase
        except ImportError:
            pytest.skip("DeepEval not installed")
        
        from pydantic import BaseModel
        
        class CompetitorList(BaseModel):
            competitors: list[dict]
            sources: list[str] = []
        
        case = next(c for c in refine_test_cases if c["id"] == "competitors-add-more")
        
        messages = build_refine_prompt(
            original_output=case["original_output"],
            output_schema_name=case["output_schema_name"],
            user_feedback=case["user_feedback"],
            additional_context=case.get("additional_context", ""),
        )
        
        result = await real_llm_call(messages, CompetitorList)
        
        test_case = LLMTestCase(
            input=f"Original: {json.dumps(case['original_output'])}\nFeedback: {case['user_feedback']}",
            actual_output=json.dumps(result.model_dump()),
            expected_output=case["expected_behavior"],
        )
        
        refinement_quality_metric.measure(test_case)
        
        assert refinement_quality_metric.score >= 0.6, (
            f"Refinement quality score {refinement_quality_metric.score} below threshold. "
            f"Reason: {refinement_quality_metric.reason}"
        )

    @pytest.mark.asyncio
    async def test_feedback_adherence_score(
        self,
        check_api_keys,
        real_llm_call,
        refine_test_cases,
        feedback_adherence_metric,
    ):
        """Test that refinement directly addresses user feedback."""
        try:
            from deepeval.test_case import LLMTestCase
        except ImportError:
            pytest.skip("DeepEval not installed")
        
        from pydantic import BaseModel
        from typing import Optional
        
        class ProductProfile(BaseModel):
            name: str
            pricing: str
            has_mobile_app: bool
            features: list[str]
        
        case = next(c for c in refine_test_cases if c["id"] == "profile-wrong-info")
        
        messages = build_refine_prompt(
            original_output=case["original_output"],
            output_schema_name=case["output_schema_name"],
            user_feedback=case["user_feedback"],
            additional_context=case.get("additional_context", ""),
        )
        
        result = await real_llm_call(messages, ProductProfile)
        
        test_case = LLMTestCase(
            input=f"Feedback: {case['user_feedback']}",
            actual_output=json.dumps(result.model_dump()),
        )
        
        feedback_adherence_metric.measure(test_case)
        
        assert feedback_adherence_metric.score >= 0.7, (
            f"Feedback adherence score {feedback_adherence_metric.score} below threshold. "
            f"Reason: {feedback_adherence_metric.reason}"
        )
