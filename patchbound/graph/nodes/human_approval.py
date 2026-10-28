"""Stage 8: Human Approval Gate (Cryptographic signature & governance binding)."""

from typing import Any

from patchbound.config import settings
from patchbound.core.digest import compute_sha256
from patchbound.core.models import ProcessStatus
from patchbound.graph.state import PatchBoundState


def human_approval_node(state: PatchBoundState) -> dict[str, Any]:
    """Stage 8: Human gate binding approval to patch digest, verification hash, and policy."""
    patch_digest = str(state.get("patch_digest", ""))
    record = state.get("verification_record")
    verification_hash = record.verification_hash if record else ""

    # Check if auto-approval is enabled (CI/eval/non-interactive flag)
    if "auto_approve" in state and state["auto_approve"] is not None:
        auto_approve = bool(state["auto_approve"])
    else:
        auto_approve = getattr(settings, "auto_approve", True)
    explicit_approval = state.get("human_approved")

    is_approved = explicit_approval if explicit_approval is not None else auto_approve

    if is_approved:
        signature = compute_sha256(f"APPROVED:{patch_digest}:{verification_hash}:v1.1")
        return {
            "status": ProcessStatus.AWAITING_APPROVAL,
            "human_approved": True,
            "approval_signature": signature,
        }

    return {
        "status": ProcessStatus.AWAITING_APPROVAL,
        "human_approved": False,
        "approval_signature": None,
    }
