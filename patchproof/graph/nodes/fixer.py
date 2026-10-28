"""Stage 5: Fixer (Single Structured LLM Call)."""

from typing import Any

from patchproof.core.models import ProcessStatus
from patchproof.graph.state import PatchProofState


def fixer_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 5: Synthesize a repair plan and anchored edits in a single structured call."""
    f2p = state.get("f2p_test_ids", [])

    # In production, calls strong model using native schema constraints.
    # Anchored edits specify file_path, old_text, and new_text.
    repair_plan = f"Apply minimal fix to address failure in {f2p[0] if f2p else 'target'}."
    anchored_edits = state.get("anchored_edits", [])

    return {
        "status": ProcessStatus.FIXING,
        "repair_plan": repair_plan,
        "target_tests": f2p,
        "anchored_edits": anchored_edits,
    }
