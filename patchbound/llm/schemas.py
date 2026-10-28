"""Pydantic schemas for LLM structured outputs."""

from pydantic import BaseModel, Field

from patchbound.core.models import AnchoredEdit


class TriageOutput(BaseModel):
    """Structured output for log triage fallback."""

    test_id: str = Field(description="Identified test name or path")
    error_type: str = Field(description="Normalized error type")
    normalized_message: str = Field(
        description="Error message with transient timestamps and hex removed"
    )


class FixerPlanOutput(BaseModel):
    """Structured output from the Fixer node."""

    repair_plan: str = Field(
        description="Causal hypothesis, intervention logic, and repair description"
    )
    target_tests: list[str] = Field(description="Test IDs expected to flip to pass")
    anchored_edits: list[AnchoredEdit] = Field(description="List of anchored text edits")


class ReviewerOutput(BaseModel):
    """Structured output from the Blind Reviewer node."""

    independent_summary: str = Field(description="Objective description of what the diff changes")
    potential_risks: list[str] = Field(
        default_factory=list, description="Potential regressions or unhandled edge cases"
    )
    verdict: str = Field(description="'approved', 'rejected', or 'probe_required'")
    probe_test_code: str | None = Field(
        default=None, description="Optional probe test to falsify repair"
    )
