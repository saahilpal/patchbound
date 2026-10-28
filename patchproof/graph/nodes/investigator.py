"""Stage 4: Investigator (Bounded LLM Agent Loop)."""

from patchproof.core.models import ProcessStatus
from patchproof.graph.state import PatchProofState
from patchproof.ledger.claim import ClaimItem, ClaimType


def investigator_node(state: PatchProofState) -> dict:
    """Stage 4: Investigate root cause using read-only tools and interventional experiments."""
    active_sig = state.get("active_failure_signature")
    test_id = active_sig.test_id if active_sig else "unknown"

    # In production, this executes the bounded agent loop with read-only tools
    # and scratchpad experiments to validate causality.
    hypotheses = [
        f"Hypothesis 1: Root cause of {test_id} is unhandled edge case in parser."
    ]

    claims = [
        ClaimItem(
            claim_id="CLM-001",
            claim_type=ClaimType.OBSERVED,
            statement=f"Test {test_id} failed with error {active_sig.error_type if active_sig else 'unknown'}.",
            evidence_ids=["EV-BASELINE-01"],
            confidence="high",
        )
    ]

    return {
        "status": ProcessStatus.INVESTIGATING,
        "hypotheses": hypotheses,
        "claims": claims,
        "evidence_ids": ["EV-BASELINE-01"],
    }
