"""Role-tiered, multi-provider LLM Gateway with budget caps, egress sanitization, and structured outputs."""

import json
import re
import time
from typing import Any

import httpx

from patchbound.config import settings
from patchbound.core.credentials import CredentialStore
from patchbound.llm.egress import EgressGate
from patchbound.llm.schemas import FixerPlanOutput, ReviewerOutput


class BudgetExceededError(Exception):
    """Raised when total token or cost budget is exhausted."""

    pass


class LLMGatewayError(Exception):
    """Raised when an external LLM API call fails."""

    pass


class LLMGateway:
    """Manages role-tiered model routing, budget accounting, prompt caching, and sanitization across providers."""

    def __init__(
        self,
        max_tokens: int | None = None,
        anthropic_key: str | None = None,
        gemini_key: str | None = None,
        openai_key: str | None = None,
    ):
        self.max_tokens = max_tokens or settings.max_tokens_total
        self.total_tokens_consumed = 0
        store = CredentialStore()
        self.anthropic_key = anthropic_key or store.get_key("anthropic")
        self.gemini_key = gemini_key or store.get_key("gemini")
        self.openai_key = openai_key or store.get_key("openai")

    def has_active_provider(self) -> bool:
        """Check whether at least one real LLM provider API key is configured."""
        return bool(self.anthropic_key or self.gemini_key or self.openai_key)

    def _track_tokens(self, prompt: str, completion: str = "") -> None:
        """Track consumed tokens with budget guardrail."""
        est_tokens = len(prompt.split()) * 2 + len(completion.split()) * 2
        if self.total_tokens_consumed + est_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.total_tokens_consumed + est_tokens} > {self.max_tokens}"
            )
        self.total_tokens_consumed += est_tokens

    def query(self, prompt: str, system_prompt: str = "", role: str = "strong") -> str:
        """Sanitize prompt, enforce budget, and route query to designated role tier."""
        sanitized_prompt = EgressGate.sanitize_text(prompt)
        sanitized_sys = EgressGate.sanitize_text(system_prompt) if system_prompt else ""
        self._track_tokens(sanitized_prompt)

        # 1. Prefer Anthropic Claude if configured
        if self.anthropic_key:
            return self._call_anthropic(sanitized_prompt, sanitized_sys, role)

        # 2. Gemini fallback
        if self.gemini_key:
            return self._call_gemini(sanitized_prompt, sanitized_sys, role)

        # 3. OpenAI fallback
        if self.openai_key:
            return self._call_openai(sanitized_prompt, sanitized_sys, role)

        # 4. Deterministic spine fallback for offline / test environments
        return f"[MOCK_RESPONSE_FOR_{role.upper()}]"

    def _call_anthropic(self, prompt: str, system_prompt: str, role: str) -> str:
        """Call Anthropic Claude API via httpx with prompt caching."""
        model = (
            settings.model_strong
            if role in ["strong", "fixer"]
            else (settings.model_reviewer if role == "reviewer" else settings.model_fast)
        )
        if "claude" not in model.lower():
            model = "claude-3-7-sonnet-20250219"

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }
        if system_prompt:
            payload["system"] = [
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
            ]

        # Retry with exponential backoff on rate limits
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 429:
                        time.sleep(2**attempt)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    content_blocks = data.get("content", [])
                    text_parts = [
                        b.get("text", "") for b in content_blocks if b.get("type") == "text"
                    ]
                    completion = "".join(text_parts)
                    self._track_tokens("", completion)
                    return completion
            except Exception as e:
                if attempt == 2:
                    raise LLMGatewayError(f"Anthropic API call failed: {e}") from e
                time.sleep(1.0)

        return ""

    def _call_gemini(self, prompt: str, system_prompt: str, role: str) -> str:
        """Call Google Gemini API via httpx."""
        model = settings.model_fast if role == "fast" else "gemini-1.5-pro"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        headers = {"content-type": "application/json"}

        contents = []
        if system_prompt:
            contents.append(
                {"role": "user", "parts": [{"text": f"System Instructions:\n{system_prompt}"}]}
            )
            contents.append(
                {
                    "role": "model",
                    "parts": [{"text": "Understood. I will strictly follow the instructions."}],
                }
            )
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {"contents": contents}

        for attempt in range(3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 429:
                        time.sleep(2**attempt)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        completion = "".join(p.get("text", "") for p in parts)
                        self._track_tokens("", completion)
                        return completion
            except Exception as e:
                if attempt == 2:
                    raise LLMGatewayError(f"Gemini API call failed: {e}") from e
                time.sleep(1.0)

        return ""

    def _call_openai(self, prompt: str, system_prompt: str, role: str) -> str:
        """Call OpenAI API via httpx."""
        model = "gpt-4o"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "content-type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": model, "messages": messages, "temperature": 0.1}

        for attempt in range(3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 429:
                        time.sleep(2**attempt)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        completion = str(choices[0].get("message", {}).get("content", ""))
                        self._track_tokens("", completion)
                        return completion
            except Exception as e:
                if attempt == 2:
                    raise LLMGatewayError(f"OpenAI API call failed: {e}") from e
                time.sleep(1.0)

        return ""

    def synthesize_repair_plan(self, prompt: str, system_prompt: str) -> FixerPlanOutput | None:
        """Query LLM and parse response into a validated FixerPlanOutput structured schema."""
        raw_response = self.query(prompt, system_prompt=system_prompt, role="strong")
        if not raw_response or "[MOCK_RESPONSE" in raw_response:
            return None

        # Extract JSON from markdown fences if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw_response)
        json_str = json_match.group(1) if json_match else raw_response

        try:
            data = json.loads(json_str)
            return FixerPlanOutput.model_validate(data)
        except Exception:
            # Fallback: search for outermost JSON object { ... }
            brace_match = re.search(r"(\{[\s\S]*\})", json_str)
            if brace_match:
                try:
                    data = json.loads(brace_match.group(1))
                    return FixerPlanOutput.model_validate(data)
                except Exception:
                    pass
            return None

    def synthesize_review(self, prompt: str, system_prompt: str) -> ReviewerOutput | None:
        """Query LLM and parse response into a validated ReviewerOutput structured schema."""
        raw_response = self.query(prompt, system_prompt=system_prompt, role="reviewer")
        if not raw_response or "[MOCK_RESPONSE" in raw_response:
            return None

        json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw_response)
        json_str = json_match.group(1) if json_match else raw_response

        try:
            data = json.loads(json_str)
            return ReviewerOutput.model_validate(data)
        except Exception:
            # Fallback: search for outermost JSON object { ... }
            brace_match = re.search(r"(\{[\s\S]*\})", json_str)
            if brace_match:
                try:
                    data = json.loads(brace_match.group(1))
                    return ReviewerOutput.model_validate(data)
                except Exception:
                    pass
            return None
