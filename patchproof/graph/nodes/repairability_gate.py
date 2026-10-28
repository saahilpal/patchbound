"""Stage 3: Repairability Gate (Deterministic Policy)."""

from typing import Any

from patchproof.core.models import OutcomeResult, ProcessStatus
from patchproof.graph.state import PatchProofState


def repairability_gate_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 3: Decide between active repair or immediate diagnosis-only report."""
    classification = state.get("reproduce_classification", "not_reproducible")

    if classification == "reproduced":
        return {
            "status": ProcessStatus.INVESTIGATING,
        }

    # Non-repairable failures exit cleanly
    if classification == "flaky":
        outcome = OutcomeResult.FLAKY
    elif classification == "not_reproducible":
        outcome = OutcomeResult.NOT_REPRODUCIBLE
    else:
        outcome = OutcomeResult.DIAGNOSIS_ONLY

    return {
        "status": ProcessStatus.TERMINATED,
        "outcome": outcome,
    }
