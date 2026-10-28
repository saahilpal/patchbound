"""Core data models and schemas for PatchProof."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ProcessStatus(StrEnum):
    """Internal execution state of the PatchProof pipeline."""

    INITIALIZING = "initializing"
    REPRODUCING = "reproducing"
    TRIAGING = "triaging"
    INVESTIGATING = "investigating"
    FIXING = "fixing"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    AWAITING_APPROVAL = "awaiting_approval"
    EXPORTING = "exporting"
    TERMINATED = "terminated"


class OutcomeResult(StrEnum):
    """Terminal business outcome classification."""

    VERIFIED_EXPORTED = "verified_exported"
    VERIFIED_REJECTED = "verified_rejected"
    UNVERIFIED_CANDIDATE = "unverified_candidate"
    DIAGNOSIS_ONLY = "diagnosis_only"
    NOT_REPRODUCIBLE = "not_reproducible"
    FLAKY = "flaky"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ERROR = "error"


class StackFrame(BaseModel):
    """A single stack frame from a failure traceback."""

    file_path: str
    line_number: int
    function_name: str
    code_context: str | None = None


class FailureSignature(BaseModel):
    """Fingerprint uniquely identifying a test failure."""

    signature_id: str = Field(description="SHA-256 fingerprint hash")
    test_id: str = Field(description="Fully-qualified test ID (e.g. tests/test_foo.py::test_bar)")
    error_type: str = Field(description="Exception or failure type name")
    normalized_message: str = Field(description="Error message with volatile tokens stripped")
    top_frame: StackFrame | None = None
    raw_output_cas_ref: str | None = Field(default=None, description="CAS reference to raw output log")


class AnchoredEdit(BaseModel):
    """A deterministic edit anchored by exact matching text."""

    file_path: str = Field(description="Repository-relative target file path")
    old_text: str = Field(description="Exact snippet to find and replace. Must match uniquely.")
    new_text: str = Field(description="Replacement text snippet")
    rationale: str | None = Field(default=None, description="Optional explanation of edit")


class FixerOutput(BaseModel):
    """Structured output from the Fixer LLM."""

    repair_plan: str = Field(description="Causal repair plan and testable predictions")
    target_tests: list[str] = Field(description="List of test IDs expected to pass")
    edits: list[AnchoredEdit] = Field(description="Ordered sequence of anchored edits")


class VerificationLevel(StrEnum):
    """Verification tiers."""

    V0_FAILED = "V0"
    V1_TARGET = "V1"
    V2_IMPACT = "V2"
    V3_CI_CLEAN = "V3"


class VerificationFlags(BaseModel):
    """Safety and quality flags accompanying a verification run."""

    flake_checked: bool = False
    pinned_tests: bool = False
    policy_clean: bool = False


class VerificationRecord(BaseModel):
    """Complete audit record of a verification execution."""

    attempt: int
    level: VerificationLevel
    flags: VerificationFlags
    f2p_executed: list[str] = Field(default_factory=list)
    f2p_passed: list[str] = Field(default_factory=list)
    f2p_failed: list[str] = Field(default_factory=list)
    p2p_regressed: list[str] = Field(default_factory=list)
    total_executed: int = 0
    total_skipped: int = 0
    patch_digest: str = ""
    verification_hash: str = ""


class FailureDelta(BaseModel):
    """Comparison between previous and current verification failures."""

    attempt: int
    max_attempts: int
    delta_type: str  # SAME_FAILURE, SECONDARY_ERROR, REGRESSION, RESOLVED
    base_failure: FailureSignature | None = None
    current_failure: FailureSignature | None = None
    regressions: list[str] = Field(default_factory=list)
    guidance: str
