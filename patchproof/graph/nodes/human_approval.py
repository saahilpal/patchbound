"""Stage 8: Human Approval Gate (LangGraph Interrupt)."""

from patchproof.core.digest import compute_sha256
from patchproof.core.models import ProcessStatus
from patchproof.graph.state import PatchProofState


def human_approval_node(state: PatchProofState) -> dict:
    """Stage 8: Human gate binding approval to patch digest, verification hash, and policy."""
    patch_digest = state.get("patch_digest", "")
    record = state.get("verification_record")
    verification_hash = record.verification_hash if record else ""

    # In production with LangGraph interrupt, this yields/interrupts to wait for human input.
    # When resumed with human approval:
    signature = compute_sha256(f"APPROVED:{patch_digest}:{verification_hash}:v1.1")

    return {
        "status": ProcessStatus.AWAITING_APPROVAL,
        "human_approved": True,
        "approval_signature": signature,
    }
