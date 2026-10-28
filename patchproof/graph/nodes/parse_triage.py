"""Stage 2: Parse and Triage (Deterministic with LLM fallback)."""

from patchproof.core.models import ProcessStatus
from patchproof.graph.state import PatchProofState


def parse_triage_node(state: PatchProofState) -> dict:
    """Stage 2: Extract normalized failure signatures, using cheap LLM fallback only if needed."""
    signatures = state.get("failure_signatures", [])

    if not signatures and state.get("reproduce_classification") == "reproduced":
        # Unrecognized log format: In production this calls fast model gateway
        # to extract (test_id, error_type, message)
        pass

    active_sig = state.get("active_failure_signature")
    if not active_sig and signatures:
        active_sig = signatures[0]

    return {
        "status": ProcessStatus.TRIAGING,
        "active_failure_signature": active_sig,
    }
