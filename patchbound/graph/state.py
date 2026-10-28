"""State definition and reducers for the PatchBound LangGraph pipeline."""

from typing import Annotated

from typing_extensions import TypedDict

from patchbound.core.models import (
    AnchoredEdit,
    FailureDelta,
    FailureSignature,
    OutcomeResult,
    ProcessStatus,
    VerificationRecord,
)
from patchbound.ledger.claim import ClaimItem


def append_unique_evidence(existing: list[str] | None, new_items: list[str]) -> list[str]:
    """Reducer that appends and deduplicates evidence IDs."""
    existing_list = existing or []
    seen = set(existing_list)
    result = list(existing_list)
    for item in new_items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def append_unique_claims(
    existing: list[ClaimItem] | None, new_claims: list[ClaimItem]
) -> list[ClaimItem]:
    """Reducer that appends and deduplicates claims by claim_id."""
    existing_list = existing or []
    seen = {c.claim_id for c in existing_list}
    result = list(existing_list)
    for c in new_claims:
        if c.claim_id not in seen:
            result.append(c)
            seen.add(c.claim_id)
    return result


class PatchBoundState(TypedDict, total=False):
    """The central state dictionary carried through the LangGraph 9-stage pipeline."""

    # Identifiers & Metadata
    investigation_id: str
    repo_path: str
    reproduce_cmd: list[str]
    reproduce_command: list[str]
    attempt: int
    max_attempts: int

    # Status & Outcomes
    status: ProcessStatus
    outcome: OutcomeResult

    # Reproduction & Triage (Stages 1-3)
    reproduce_classification: str  # reproduced, flaky, not_reproducible, env_mismatch
    f2p_test_ids: list[str]
    p2p_test_ids: list[str]
    failure_signatures: list[FailureSignature]
    active_failure_signature: FailureSignature | None

    # Investigation & Causal Ledger (Stage 4)
    context_mode: str | None
    target_file: str | None
    target_symbol: str | None
    code_context: str | None
    hypotheses: list[str]
    claims: Annotated[list[ClaimItem], append_unique_claims]
    evidence_ids: Annotated[list[str], append_unique_evidence]

    # Repair & Fixer (Stage 5)
    repair_plan: str
    target_tests: list[str]
    anchored_edits: list[AnchoredEdit]
    alternative_anchored_edits: list[AnchoredEdit]

    # Verification (Stage 6)
    canonical_diff: str
    patch_digest: str
    verification_record: VerificationRecord | None
    failure_delta: FailureDelta | None
    patched_workspace_path: str | None

    # Review & Anti-cheat (Stage 7)
    review_status: str  # approved, rejected, probe_required
    review_notes: str

    # Human Gate (Stage 8)
    auto_approve: bool
    human_approved: bool
    approval_signature: str | None

    # Final Export & Report (Stage 9)
    final_report_markdown: str
    exported_patch_path: str | None
    export_path: str | None
    feedback: str | None
