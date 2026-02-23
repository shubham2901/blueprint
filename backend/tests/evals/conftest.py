"""
Blueprint Backend — LLM Evaluation Test Fixtures

These fixtures are for prompt evaluation tests that make REAL LLM calls.
Used to validate prompt quality, not for regression testing.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# -----------------------------------------------------------------------------
# Environment Setup
# -----------------------------------------------------------------------------

# These tests require real API keys
# They will be skipped if GEMINI_API_KEY is not set to a real value


def is_real_api_key(key: str | None) -> bool:
    """Check if API key looks like a real key (not a test placeholder)."""
    if not key:
        return False
    if key.startswith("test-"):
        return False
    if len(key) < 20:
        return False
    return True


@pytest.fixture(scope="session")
def check_api_keys():
    """Skip eval tests if real API keys are not available."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if not is_real_api_key(gemini_key):
        pytest.skip("Real GEMINI_API_KEY required for evaluation tests")


# -----------------------------------------------------------------------------
# Test Case Loaders
# -----------------------------------------------------------------------------


def load_test_cases(filename: str) -> list[dict]:
    """Load test cases from JSON file in datasets directory."""
    datasets_dir = Path(__file__).parent / "datasets"
    filepath = datasets_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Test case file not found: {filepath}")
    
    with open(filepath, "r") as f:
        return json.load(f)


@pytest.fixture
def classify_test_cases() -> list[dict]:
    """Load classify prompt test cases."""
    return load_test_cases("classify_cases.json")


@pytest.fixture
def competitors_test_cases() -> list[dict]:
    """Load competitors prompt test cases."""
    return load_test_cases("competitors_cases.json")


@pytest.fixture
def refine_test_cases() -> list[dict]:
    """Load refine prompt test cases."""
    return load_test_cases("refine_cases.json")


# -----------------------------------------------------------------------------
# LLM Call Helpers
# -----------------------------------------------------------------------------


@pytest.fixture
async def real_llm_call():
    """
    Fixture that provides a function to make real LLM calls.
    Uses the actual app's LLM module with real API calls.
    """
    from app.llm import call_llm_structured
    
    async def _call(messages: list[dict], response_model: type) -> Any:
        """Make a real LLM call with structured output."""
        return await call_llm_structured(
            messages=messages,
            response_model=response_model,
            journey_id="eval-test"
        )
    
    return _call


# -----------------------------------------------------------------------------
# Evaluation Metrics (DeepEval)
# -----------------------------------------------------------------------------


@pytest.fixture
def intent_accuracy_metric():
    """
    Custom metric for evaluating intent classification accuracy.
    Uses DeepEval's GEval for LLM-as-a-judge evaluation.
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
        
        return GEval(
            name="Intent Accuracy",
            criteria=(
                "The classified intent (build/explore/improve/small_talk/off_topic) "
                "correctly matches the user's actual intent based on their input. "
                "Consider the trigger words and patterns described in the prompt."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            threshold=0.7,
        )
    except ImportError:
        pytest.skip("DeepEval not installed")


@pytest.fixture
def domain_accuracy_metric():
    """
    Custom metric for evaluating domain extraction accuracy.
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
        
        return GEval(
            name="Domain Accuracy",
            criteria=(
                "The extracted domain correctly identifies the product/market "
                "category from the user's input. The domain should be specific "
                "(e.g., 'Note-taking' not just 'Productivity')."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            threshold=0.7,
        )
    except ImportError:
        pytest.skip("DeepEval not installed")


@pytest.fixture
def json_validity_metric():
    """
    Metric for checking JSON output validity.
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
        
        return GEval(
            name="JSON Validity",
            criteria=(
                "The output is valid JSON that matches the expected schema. "
                "All required fields are present and have appropriate types."
            ),
            evaluation_params=[
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            threshold=0.9,
        )
    except ImportError:
        pytest.skip("DeepEval not installed")


@pytest.fixture
def clarification_quality_metric():
    """
    Metric for evaluating clarification question quality.
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
        
        return GEval(
            name="Clarification Quality",
            criteria=(
                "The clarification questions are relevant to the user's input, "
                "mutually exclusive in their options, and would meaningfully "
                "narrow the research space. Questions should not re-ask what "
                "the user already specified in their input."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            threshold=0.7,
        )
    except ImportError:
        pytest.skip("DeepEval not installed")


@pytest.fixture
def refinement_quality_metric():
    """
    Metric for evaluating refinement quality - how well the LLM addresses user feedback.
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
        
        return GEval(
            name="Refinement Quality",
            criteria=(
                "The refined output addresses the user's feedback while maintaining "
                "the quality and validity of the original content. Key aspects: "
                "1) The specific feedback request is addressed "
                "2) Existing good content is preserved (not unnecessarily removed) "
                "3) New content is relevant and grounded "
                "4) The output schema/structure is maintained "
                "5) Overall quality is equal to or better than original"
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            threshold=0.7,
        )
    except ImportError:
        pytest.skip("DeepEval not installed")


@pytest.fixture
def feedback_adherence_metric():
    """
    Metric for evaluating how directly the refinement addresses user feedback.
    """
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
        
        return GEval(
            name="Feedback Adherence",
            criteria=(
                "The refined output directly addresses the user's feedback request. "
                "If the user asked for 'more X', there should be more X. "
                "If the user asked for 'simpler', it should be simpler. "
                "If the user corrected an error, the error should be fixed. "
                "The feedback should not be ignored or only partially addressed."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            threshold=0.8,
        )
    except ImportError:
        pytest.skip("DeepEval not installed")


# -----------------------------------------------------------------------------
# DeepEval Setup
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def setup_deepeval():
    """Configure DeepEval for evaluation tests."""
    try:
        import deepeval
        
        # Use Gemini as the judge model (cheaper than GPT-4)
        # DeepEval will use the GEMINI_API_KEY from environment
        os.environ.setdefault("DEEPEVAL_LLM_MODEL", "gemini/gemini-2.0-flash")
        
    except ImportError:
        pass  # DeepEval not installed, tests will be skipped


# -----------------------------------------------------------------------------
# Result Caching (to avoid repeated LLM calls)
# -----------------------------------------------------------------------------


_eval_cache: dict[str, Any] = {}


@pytest.fixture
def eval_cache():
    """
    Simple cache to avoid repeated LLM calls for the same input.
    Useful when running multiple metrics on the same output.
    """
    return _eval_cache


def get_cached_result(cache_key: str) -> Any | None:
    """Get cached evaluation result."""
    return _eval_cache.get(cache_key)


def set_cached_result(cache_key: str, result: Any) -> None:
    """Cache evaluation result."""
    _eval_cache[cache_key] = result
