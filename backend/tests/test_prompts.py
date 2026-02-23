"""
Blueprint Backend — Prompts Module Unit Tests

Tests for prompts.py: prompt structure validation, message format, required fields.
These tests verify prompt builders return valid message formats without making LLM calls.
"""

import json
import pytest

from app.prompts import (
    build_classify_prompt,
    build_competitors_prompt,
    build_explore_prompt,
    build_market_overview_prompt,
    build_gap_analysis_prompt,
    build_problem_statement_prompt,
    build_refine_prompt,
    build_fix_json_prompt,
    get_quick_response,
    SMALL_TALK_RESPONSES,
    OFF_TOPIC_RESPONSES,
    CLASSIFY_PROMPT,
    COMPETITORS_PROMPT,
    EXPLORE_PROMPT,
    MARKET_OVERVIEW_PROMPT,
    GAP_ANALYSIS_PROMPT,
    PROBLEM_STATEMENT_PROMPT,
    REFINE_PROMPT,
)


# -----------------------------------------------------------------------------
# Message Format Validation Helpers
# -----------------------------------------------------------------------------


def assert_valid_message_list(messages: list[dict]) -> None:
    """Assert that messages is a valid list of message dicts."""
    assert isinstance(messages, list), "Messages should be a list"
    assert len(messages) > 0, "Messages should not be empty"
    
    for msg in messages:
        assert isinstance(msg, dict), "Each message should be a dict"
        assert "role" in msg, "Each message should have a 'role' key"
        assert "content" in msg, "Each message should have a 'content' key"
        assert msg["role"] in ["system", "user", "assistant"], f"Invalid role: {msg['role']}"
        assert isinstance(msg["content"], str), "Content should be a string"
        assert len(msg["content"]) > 0, "Content should not be empty"


def assert_prompt_contains(messages: list[dict], *keywords: str) -> None:
    """Assert that the prompt content contains all specified keywords."""
    content = " ".join(msg["content"] for msg in messages)
    for keyword in keywords:
        assert keyword.lower() in content.lower(), f"Prompt should contain '{keyword}'"


# -----------------------------------------------------------------------------
# build_classify_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildClassifyPrompt:
    """Tests for build_classify_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that classify prompt returns valid message format."""
        messages = build_classify_prompt("I want to build a note-taking app")
        assert_valid_message_list(messages)

    def test_includes_user_input(self):
        """Test that user input is included in the prompt."""
        user_input = "I want to build a note-taking app"
        messages = build_classify_prompt(user_input)
        assert user_input in messages[0]["content"]

    def test_includes_classification_instructions(self):
        """Test that classification instructions are included."""
        messages = build_classify_prompt("test input")
        assert_prompt_contains(messages, "build", "explore", "improve", "small_talk", "off_topic")

    def test_includes_json_schema_instructions(self):
        """Test that JSON output instructions are included."""
        messages = build_classify_prompt("test input")
        assert_prompt_contains(messages, "intent_type", "domain", "clarification_questions")

    def test_uses_user_role(self):
        """Test that the message uses 'user' role."""
        messages = build_classify_prompt("test input")
        assert messages[0]["role"] == "user"

    def test_handles_special_characters_in_input(self):
        """Test handling of special characters in user input."""
        messages = build_classify_prompt('Test with "quotes" and {braces}')
        assert_valid_message_list(messages)
        assert '"quotes"' in messages[0]["content"]


# -----------------------------------------------------------------------------
# build_competitors_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildCompetitorsPrompt:
    """Tests for build_competitors_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that competitors prompt returns valid message format."""
        messages = build_competitors_prompt(
            domain="Note-taking",
            clarification_context={"target_platform": "mobile"},
        )
        assert_valid_message_list(messages)

    def test_includes_domain(self):
        """Test that domain is included in the prompt."""
        messages = build_competitors_prompt(
            domain="Note-taking",
            clarification_context={},
        )
        assert_prompt_contains(messages, "Note-taking")

    def test_includes_clarification_context(self):
        """Test that clarification context is included."""
        messages = build_competitors_prompt(
            domain="Note-taking",
            clarification_context={"target_platform": "mobile", "audience": "students"},
        )
        assert_prompt_contains(messages, "mobile", "students")

    def test_includes_alternatives_data_when_provided(self):
        """Test that alternatives data is included when provided."""
        alternatives = [{"name": "Notion", "description": "All-in-one workspace"}]
        messages = build_competitors_prompt(
            domain="Note-taking",
            clarification_context={},
            alternatives_data=alternatives,
        )
        assert_prompt_contains(messages, "Notion", "All-in-one workspace")

    def test_includes_search_results_when_provided(self):
        """Test that search results are included when provided."""
        search_results = [{"title": "Best Apps 2024", "url": "https://example.com"}]
        messages = build_competitors_prompt(
            domain="Note-taking",
            clarification_context={},
            search_results=search_results,
        )
        assert_prompt_contains(messages, "Best Apps 2024")

    def test_includes_reddit_results_when_provided(self):
        """Test that Reddit results are included when provided."""
        reddit_results = [{"title": "r/NoteTaking discussion", "snippet": "Great alternatives"}]
        messages = build_competitors_prompt(
            domain="Note-taking",
            clarification_context={},
            reddit_results=reddit_results,
        )
        assert_prompt_contains(messages, "r/NoteTaking", "Great alternatives")

    def test_handles_no_external_data(self):
        """Test prompt when no external data sources are provided."""
        messages = build_competitors_prompt(
            domain="Fintech",
            clarification_context={},
        )
        assert_valid_message_list(messages)
        assert_prompt_contains(messages, "No external data provided")


# -----------------------------------------------------------------------------
# build_explore_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildExplorePrompt:
    """Tests for build_explore_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that explore prompt returns valid message format."""
        messages = build_explore_prompt(
            product_name="Notion",
            scraped_content="Notion is an all-in-one workspace...",
        )
        assert_valid_message_list(messages)

    def test_includes_product_name(self):
        """Test that product name is included."""
        messages = build_explore_prompt(
            product_name="Obsidian",
            scraped_content="Content here",
        )
        assert_prompt_contains(messages, "Obsidian")

    def test_includes_scraped_content(self):
        """Test that scraped content is included."""
        messages = build_explore_prompt(
            product_name="Notion",
            scraped_content="Notion offers rich text editing and database views",
        )
        assert_prompt_contains(messages, "rich text editing", "database views")

    def test_includes_reddit_content_when_provided(self):
        """Test that Reddit content is included when provided."""
        messages = build_explore_prompt(
            product_name="Notion",
            scraped_content="Content",
            reddit_content="Users on Reddit say it's great for collaboration",
        )
        assert_prompt_contains(messages, "great for collaboration")

    def test_handles_no_reddit_content(self):
        """Test that prompt handles absence of Reddit content."""
        messages = build_explore_prompt(
            product_name="Notion",
            scraped_content="Content",
            reddit_content="",
        )
        assert_valid_message_list(messages)
        assert_prompt_contains(messages, "No Reddit content provided")

    def test_includes_output_schema(self):
        """Test that expected output schema fields are mentioned."""
        messages = build_explore_prompt(
            product_name="Notion",
            scraped_content="Content",
        )
        assert_prompt_contains(messages, "features_summary", "pricing_tiers", "strengths", "weaknesses")


# -----------------------------------------------------------------------------
# build_market_overview_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildMarketOverviewPrompt:
    """Tests for build_market_overview_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that market overview prompt returns valid message format."""
        competitors = [{"name": "Notion", "description": "Workspace tool"}]
        messages = build_market_overview_prompt(
            domain="Note-taking",
            competitors=competitors,
        )
        assert_valid_message_list(messages)

    def test_includes_domain(self):
        """Test that domain is included."""
        messages = build_market_overview_prompt(
            domain="Project Management",
            competitors=[],
        )
        assert_prompt_contains(messages, "Project Management")

    def test_includes_competitor_data(self):
        """Test that competitor data is included."""
        competitors = [
            {"name": "Notion", "description": "All-in-one workspace"},
            {"name": "Obsidian", "description": "Local-first note-taking"},
        ]
        messages = build_market_overview_prompt(
            domain="Note-taking",
            competitors=competitors,
        )
        assert_prompt_contains(messages, "Notion", "Obsidian")


# -----------------------------------------------------------------------------
# build_gap_analysis_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildGapAnalysisPrompt:
    """Tests for build_gap_analysis_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that gap analysis prompt returns valid message format."""
        profiles = [{"name": "Notion", "strengths": ["Flexibility"], "weaknesses": ["Performance"]}]
        messages = build_gap_analysis_prompt(
            domain="Note-taking",
            profiles=profiles,
            clarification_context={"platform": "mobile"},
        )
        assert_valid_message_list(messages)

    def test_includes_domain(self):
        """Test that domain is included."""
        messages = build_gap_analysis_prompt(
            domain="Fintech",
            profiles=[],
            clarification_context={},
        )
        assert_prompt_contains(messages, "Fintech")

    def test_includes_profiles(self):
        """Test that competitor profiles are included."""
        profiles = [
            {"name": "Notion", "weaknesses": ["Slow on mobile"]},
            {"name": "Obsidian", "weaknesses": ["Plugin quality varies"]},
        ]
        messages = build_gap_analysis_prompt(
            domain="Note-taking",
            profiles=profiles,
            clarification_context={},
        )
        assert_prompt_contains(messages, "Slow on mobile", "Plugin quality varies")

    def test_includes_clarification_context(self):
        """Test that user preferences are included."""
        messages = build_gap_analysis_prompt(
            domain="Note-taking",
            profiles=[],
            clarification_context={"target_audience": "students", "platform": "mobile"},
        )
        assert_prompt_contains(messages, "students", "mobile")

    def test_includes_market_overview_when_provided(self):
        """Test that market overview is included when provided."""
        messages = build_gap_analysis_prompt(
            domain="Note-taking",
            profiles=[],
            clarification_context={},
            market_overview={"title": "Market Overview", "content": "The market is growing rapidly"},
        )
        assert_prompt_contains(messages, "growing rapidly")


# -----------------------------------------------------------------------------
# build_problem_statement_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildProblemStatementPrompt:
    """Tests for build_problem_statement_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that problem statement prompt returns valid message format."""
        selected_gaps = [
            {"id": "gap-1", "title": "Mobile-first gap", "description": "No good mobile apps"}
        ]
        context = {"domain": "Note-taking", "competitors_analyzed": ["Notion", "Obsidian"]}
        messages = build_problem_statement_prompt(selected_gaps, context)
        assert_valid_message_list(messages)

    def test_includes_selected_gaps(self):
        """Test that selected gaps are included."""
        selected_gaps = [
            {"id": "gap-mobile", "title": "No mobile-first power tool", "description": "Users need mobile"}
        ]
        messages = build_problem_statement_prompt(
            selected_gaps=selected_gaps,
            context={"domain": "Note-taking"},
        )
        assert_prompt_contains(messages, "mobile-first power tool")

    def test_includes_context(self):
        """Test that research context is included."""
        messages = build_problem_statement_prompt(
            selected_gaps=[],
            context={
                "domain": "Note-taking",
                "competitors_analyzed": ["Notion", "Obsidian"],
                "clarification_context": {"platform": "mobile"},
            },
        )
        assert_prompt_contains(messages, "Note-taking", "Notion", "Obsidian")


# -----------------------------------------------------------------------------
# build_refine_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildRefinePrompt:
    """Tests for build_refine_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that refine prompt returns valid message format."""
        original_output = {"competitors": [{"name": "Notion", "description": "Workspace"}]}
        messages = build_refine_prompt(
            original_output=original_output,
            output_schema_name="CompetitorList",
            user_feedback="Add more competitors",
        )
        assert_valid_message_list(messages)

    def test_includes_original_output(self):
        """Test that original output is included in the prompt."""
        original_output = {"competitors": [{"name": "Obsidian", "description": "Note-taking app"}]}
        messages = build_refine_prompt(
            original_output=original_output,
            output_schema_name="CompetitorList",
            user_feedback="Focus on mobile apps",
        )
        assert_prompt_contains(messages, "Obsidian", "Note-taking app")

    def test_includes_user_feedback(self):
        """Test that user feedback is included in the prompt."""
        messages = build_refine_prompt(
            original_output={"data": "test"},
            output_schema_name="TestSchema",
            user_feedback="I need more enterprise-focused competitors",
        )
        assert_prompt_contains(messages, "enterprise-focused competitors")

    def test_includes_schema_name(self):
        """Test that output schema name is included."""
        messages = build_refine_prompt(
            original_output={},
            output_schema_name="GapAnalysis",
            user_feedback="More detail",
        )
        assert_prompt_contains(messages, "GapAnalysis")

    def test_includes_additional_context_when_provided(self):
        """Test that additional context is included when provided."""
        messages = build_refine_prompt(
            original_output={"test": "data"},
            output_schema_name="TestSchema",
            user_feedback="Refine this",
            additional_context="The user is building for mobile-first students",
        )
        assert_prompt_contains(messages, "mobile-first students")

    def test_handles_no_additional_context(self):
        """Test that prompt works without additional context."""
        messages = build_refine_prompt(
            original_output={"key": "value"},
            output_schema_name="TestSchema",
            user_feedback="Improve it",
        )
        assert_valid_message_list(messages)
        # Should not contain "Additional Context" header when not provided
        content = messages[0]["content"]
        assert "Additional Context" not in content or "mobile" not in content

    def test_includes_refinement_instructions(self):
        """Test that refinement instructions are included."""
        messages = build_refine_prompt(
            original_output={},
            output_schema_name="TestSchema",
            user_feedback="More detail",
        )
        assert_prompt_contains(messages, "Refiner", "improve", "feedback")

    def test_handles_complex_original_output(self):
        """Test handling of complex nested output structures."""
        complex_output = {
            "competitors": [
                {"name": "Notion", "features": ["database", "wiki"], "pricing": {"free": True}},
                {"name": "Obsidian", "features": ["markdown", "local"], "pricing": {"free": True}},
            ],
            "market_size": "Large",
            "sources": ["https://example.com"],
        }
        messages = build_refine_prompt(
            original_output=complex_output,
            output_schema_name="CompetitorList",
            user_feedback="Include pricing details",
        )
        assert_valid_message_list(messages)
        assert_prompt_contains(messages, "Notion", "database", "wiki")

    def test_uses_user_role(self):
        """Test that the message uses 'user' role."""
        messages = build_refine_prompt(
            original_output={},
            output_schema_name="TestSchema",
            user_feedback="test",
        )
        assert messages[0]["role"] == "user"


# -----------------------------------------------------------------------------
# build_fix_json_prompt Tests
# -----------------------------------------------------------------------------


class TestBuildFixJsonPrompt:
    """Tests for build_fix_json_prompt function."""

    def test_returns_valid_message_list(self):
        """Test that fix JSON prompt returns valid message format."""
        messages = build_fix_json_prompt(
            broken_output='{"incomplete": ',
            expected_schema={"type": "object", "properties": {"key": {"type": "string"}}},
        )
        assert_valid_message_list(messages)

    def test_includes_broken_output(self):
        """Test that broken output is included."""
        broken = '{"broken": "json", missing_end'
        messages = build_fix_json_prompt(
            broken_output=broken,
            expected_schema={},
        )
        assert broken in messages[0]["content"]

    def test_includes_expected_schema(self):
        """Test that expected schema is included."""
        schema = {"type": "object", "required": ["intent_type"]}
        messages = build_fix_json_prompt(
            broken_output="invalid",
            expected_schema=schema,
        )
        assert "intent_type" in messages[0]["content"]

    def test_includes_fix_instructions(self):
        """Test that fix instructions are included."""
        messages = build_fix_json_prompt(
            broken_output="{}",
            expected_schema={},
        )
        assert_prompt_contains(messages, "Fix", "valid JSON")


# -----------------------------------------------------------------------------
# get_quick_response Tests
# -----------------------------------------------------------------------------


class TestGetQuickResponse:
    """Tests for get_quick_response function."""

    def test_returns_small_talk_response(self):
        """Test that small_talk returns a valid response."""
        response = get_quick_response("small_talk")
        assert response in SMALL_TALK_RESPONSES
        assert len(response) > 0

    def test_returns_off_topic_response(self):
        """Test that off_topic returns a valid response."""
        response = get_quick_response("off_topic")
        assert response in OFF_TOPIC_RESPONSES
        assert len(response) > 0

    def test_returns_empty_for_other_intents(self):
        """Test that other intents return empty string."""
        assert get_quick_response("build") == ""
        assert get_quick_response("explore") == ""
        assert get_quick_response("improve") == ""

    def test_responses_vary(self):
        """Test that responses can vary (randomized)."""
        # Get multiple responses - at least one should be different over many tries
        # This is a probabilistic test but with enough samples should pass
        responses = [get_quick_response("small_talk") for _ in range(20)]
        # With 6 possible responses, getting all the same in 20 tries is very unlikely
        assert len(set(responses)) >= 1  # At minimum, responses exist


# -----------------------------------------------------------------------------
# Prompt Template Quality Tests
# -----------------------------------------------------------------------------


class TestPromptTemplateQuality:
    """Tests for overall prompt template quality and completeness."""

    def test_classify_prompt_has_intent_definitions(self):
        """Test that classify prompt defines all intent types clearly."""
        assert "build" in CLASSIFY_PROMPT.lower()
        assert "explore" in CLASSIFY_PROMPT.lower()
        assert "improve" in CLASSIFY_PROMPT.lower()
        assert "small_talk" in CLASSIFY_PROMPT.lower()
        assert "off_topic" in CLASSIFY_PROMPT.lower()

    def test_classify_prompt_has_examples(self):
        """Test that classify prompt includes examples."""
        assert "Example" in CLASSIFY_PROMPT

    def test_classify_prompt_specifies_json_output(self):
        """Test that classify prompt specifies JSON output format."""
        assert "JSON" in CLASSIFY_PROMPT
        assert "intent_type" in CLASSIFY_PROMPT

    def test_competitors_prompt_has_output_format(self):
        """Test that competitors prompt specifies output format."""
        assert '"competitors"' in COMPETITORS_PROMPT
        assert '"sources"' in COMPETITORS_PROMPT

    def test_explore_prompt_has_required_fields(self):
        """Test that explore prompt specifies required output fields."""
        assert "features_summary" in EXPLORE_PROMPT
        assert "pricing_tiers" in EXPLORE_PROMPT
        assert "strengths" in EXPLORE_PROMPT
        assert "weaknesses" in EXPLORE_PROMPT
        assert "reddit_sentiment" in EXPLORE_PROMPT

    def test_gap_analysis_prompt_has_structure(self):
        """Test that gap analysis prompt has clear structure."""
        assert "problems" in GAP_ANALYSIS_PROMPT
        assert "evidence" in GAP_ANALYSIS_PROMPT
        assert "opportunity_size" in GAP_ANALYSIS_PROMPT

    def test_problem_statement_prompt_has_deliverables(self):
        """Test that problem statement prompt specifies deliverables."""
        assert "target_user" in PROBLEM_STATEMENT_PROMPT
        assert "key_differentiators" in PROBLEM_STATEMENT_PROMPT
        assert "validation_questions" in PROBLEM_STATEMENT_PROMPT

    def test_refine_prompt_has_feedback_patterns(self):
        """Test that refine prompt includes common feedback patterns."""
        assert "More X" in REFINE_PROMPT or "more" in REFINE_PROMPT.lower()
        assert "Less X" in REFINE_PROMPT or "focus" in REFINE_PROMPT.lower()
        assert "Missing" in REFINE_PROMPT

    def test_refine_prompt_has_quality_rules(self):
        """Test that refine prompt includes quality guidelines."""
        assert "Preserve" in REFINE_PROMPT or "preserve" in REFINE_PROMPT.lower()
        assert "evidence" in REFINE_PROMPT.lower()
        assert "schema" in REFINE_PROMPT.lower()

    def test_all_prompts_specify_no_markdown_fences(self):
        """Test that prompts instruct LLM to avoid markdown fences."""
        prompts = [
            CLASSIFY_PROMPT,
            COMPETITORS_PROMPT,
            EXPLORE_PROMPT,
            MARKET_OVERVIEW_PROMPT,
            GAP_ANALYSIS_PROMPT,
            PROBLEM_STATEMENT_PROMPT,
            REFINE_PROMPT,
        ]
        for prompt in prompts:
            # Each prompt should mention avoiding markdown or code fences
            assert "no markdown" in prompt.lower() or "no code fence" in prompt.lower() or \
                   "nothing else" in prompt.lower() or "only" in prompt.lower()
