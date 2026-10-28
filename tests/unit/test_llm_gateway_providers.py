"""Unit tests for multi-provider LLM Gateway routing and structured schemas."""

from unittest.mock import patch

import pytest

from patchbound.llm.gateway import BudgetExceededError, LLMGateway
from patchbound.llm.schemas import FixerPlanOutput


def test_gateway_offline_fallback_when_no_keys() -> None:
    """Verify that gateway cleanly returns offline fallback without throwing errors when no keys exist."""
    gateway = LLMGateway(anthropic_key=None, gemini_key=None, openai_key=None)
    assert not gateway.has_active_provider()

    res = gateway.query("Synthesize fix for bug", role="strong")
    assert "[MOCK_RESPONSE_FOR_STRONG]" in res


def test_gateway_egress_scrubs_outbound_secrets() -> None:
    """Verify that credentials are redacted before dispatching queries."""
    fake_ant_key = "sk-ant-" + "testkey123456789012345678901234567890"
    gateway = LLMGateway(anthropic_key=fake_ant_key)
    assert gateway.has_active_provider()

    with patch.object(gateway, "_call_anthropic", return_value="Fix applied") as mock_call:
        fake_gh_pat = "ghp_" + "123456789012345678901234567890123456"
        prompt_with_secret = (
            f"Here is my secret AWS key: AKIAIOSFODNN7EXAMPLE and GitHub token {fake_gh_pat}"
        )
        res = gateway.query(prompt_with_secret, role="strong")
        assert res == "Fix applied"

        # Assert outgoing prompt was sanitized
        called_prompt = mock_call.call_args[0][0]
        assert "AKIAIOSFODNN7EXAMPLE" not in called_prompt
        assert "[REDACTED_AWS_KEY]" in called_prompt
        assert "ghp_1234567890" not in called_prompt
        assert "[REDACTED_GITHUB_PAT]" in called_prompt


def test_gateway_enforces_budget_limit() -> None:
    """Verify that BudgetExceededError is raised when token budget is exhausted."""
    gateway = LLMGateway(max_tokens=10)
    with pytest.raises(BudgetExceededError):
        gateway.query(
            "This prompt is intentionally long enough to exceed the tiny ten token budget cap."
        )


def test_synthesize_repair_plan_parses_json() -> None:
    """Verify that valid JSON from LLM is parsed into a FixerPlanOutput model."""
    gateway = LLMGateway()
    mock_json = """
    ```json
    {
      "repair_plan": "Fix subtraction to addition in add function",
      "target_tests": ["tests/test_calc.py::test_add"],
      "anchored_edits": [
        {
          "file_path": "calc.py",
          "old_text": "return a - b",
          "new_text": "return a + b"
        }
      ]
    }
    ```
    """
    with patch.object(gateway, "query", return_value=mock_json):
        plan = gateway.synthesize_repair_plan("prompt", "system")
        assert plan is not None
        assert isinstance(plan, FixerPlanOutput)
        assert len(plan.anchored_edits) == 1
        assert plan.anchored_edits[0].file_path == "calc.py"
        assert plan.anchored_edits[0].new_text == "return a + b"


def test_synthesize_repair_plan_resilient_to_prose_wrapping() -> None:
    """Verify that JSON wrapped in conversational prose without markdown fences is extracted."""
    gateway = LLMGateway()
    prose_json = """
    Sure, here is the verified repair plan for your code:
    {
      "repair_plan": "Replace multiply with divide",
      "target_tests": ["test_div"],
      "anchored_edits": [
        {
          "file_path": "math.py",
          "old_text": "a * b",
          "new_text": "a / b"
        }
      ]
    }
    Hope this helps! Let me know if you need more fixes.
    """
    with patch.object(gateway, "query", return_value=prose_json):
        plan = gateway.synthesize_repair_plan("prompt", "system")
        assert plan is not None
        assert plan.repair_plan == "Replace multiply with divide"
        assert plan.anchored_edits[0].new_text == "a / b"
