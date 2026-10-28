"""Comprehensive guardrail definitions and exception hierarchy."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GuardrailSeverity(StrEnum):
    """Severity level of a guardrail violation."""

    HARD_GATE = "hard_gate"  # Halts execution immediately; cannot be overridden
    SOFT_GATE = "soft_gate"  # Flags warning for human reviewer decision


class GuardrailViolation(Exception):
    """Raised when a hard guardrail gate is breached."""

    def __init__(self, guardrail_id: str, message: str, severity: GuardrailSeverity = GuardrailSeverity.HARD_GATE):
        super().__init__(f"[{guardrail_id}] {message}")
        self.guardrail_id = guardrail_id
        self.message = message
        self.severity = severity


class GuardrailCheckResult(BaseModel):
    """Outcome of an individual guardrail evaluation."""

    guardrail_id: str
    name: str
    passed: bool
    severity: GuardrailSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
