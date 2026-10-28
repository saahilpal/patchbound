"""Role-tiered LLM Gateway with budget caps and egress sanitization."""

from patchproof.config import settings
from patchproof.llm.egress import EgressGate


class BudgetExceededError(Exception):
    """Raised when total token or cost budget is exhausted."""
    pass


class LLMGateway:
    """Manages role-tiered model routing, budget accounting, and sanitization."""

    def __init__(self, max_tokens: int | None = None):
        self.max_tokens = max_tokens or settings.max_tokens_total
        self.total_tokens_consumed = 0

    def query(self, prompt: str, role: str = "strong") -> str:
        """Sanitize prompt, enforce budget, and route query to designated role tier."""
        sanitized_prompt = EgressGate.sanitize_text(prompt)

        # Approximate token accounting
        est_tokens = len(sanitized_prompt.split()) * 2
        if self.total_tokens_consumed + est_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.total_tokens_consumed + est_tokens} > {self.max_tokens}"
            )

        self.total_tokens_consumed += est_tokens

        # In production, routes to Gemini / Claude / OpenAI API with schema validation
        return f"[MOCK_RESPONSE_FOR_{role.upper()}]"
