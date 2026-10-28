"""Unit tests for the role-tiered LLMGateway and egress sanitization."""

import pytest

from patchproof.llm.egress import EgressGate
from patchproof.llm.gateway import BudgetExceededError, LLMGateway


def test_egress_gate_sanitizes_secrets() -> None:
    text_with_keys = (
        "Here is the config: AWS_SECRET=AKIAIOSFODNN7EXAMPLE and "
        "TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    )
    sanitized = EgressGate.sanitize_text(text_with_keys)

    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in sanitized
    assert "[REDACTED_GITHUB_PAT]" in sanitized


def test_llm_gateway_enforces_token_budget() -> None:
    gateway = LLMGateway(max_tokens=50)

    # First small query passes
    res = gateway.query("Hello model, analyze this function.", role="fast")
    assert "MOCK_RESPONSE_FOR_FAST" in res
    assert gateway.total_tokens_consumed > 0

    # Very large prompt exceeding remaining budget
    large_prompt = "word " * 100
    with pytest.raises(BudgetExceededError, match="Token budget exceeded"):
        gateway.query(large_prompt, role="strong")
