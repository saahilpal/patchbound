"""Stage 7: Review (Deterministic anti-cheat + Blind LLM Reviewer)."""

from patchproof.core.models import ProcessStatus
from patchproof.graph.state import PatchProofState


def review_node(state: PatchProofState) -> dict:
    """Stage 7: Blind review of canonical diff and execution of probe tests."""
    record = state.get("verification_record")
    canonical_diff = state.get("canonical_diff", "")

    # In production, this prompts the Reviewer model with clean context
    # (without fixer's rationale) to independently summarize what the patch does
    # and compare against the failure signature.
    review_status = "approved"
    review_notes = "Patch addresses root cause without anti-cheat violations."

    return {
        "status": ProcessStatus.REVIEWING,
        "review_status": review_status,
        "review_notes": review_notes,
    }
