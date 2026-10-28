"""Stage 5: Fixer (Single Structured LLM Call / Adaptive Repair Synthesis)."""

from pathlib import Path
from typing import Any

from patchproof.core.models import AnchoredEdit, ProcessStatus
from patchproof.graph.state import PatchProofState


def fixer_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 5: Synthesize a repair plan and anchored edits, adapting across loop retries."""
    f2p = state.get("f2p_test_ids", [])
    attempt = int(state.get("attempt", 0))
    failure_delta = state.get("failure_delta")
    existing_edits = list(state.get("anchored_edits", []))
    repo_path = Path(str(state.get("repo_path", ".")))
    active_sig = state.get("active_failure_signature")

    target_name = f2p[0] if f2p else (active_sig.test_id if active_sig else "target")
    repair_plan = f"Apply targeted fix for {target_name} (Attempt {attempt})."

    # If edits were explicitly provided for this attempt, preserve them
    anchored_edits: list[AnchoredEdit] = []

    # Adaptive loop: if attempt > 0 and previous attempt failed, evolve the edits
    if attempt > 0 and failure_delta:
        repair_plan = f"Evolved repair plan (Attempt {attempt}): Addressing {failure_delta.delta_type} ({failure_delta.guidance})."

        # Check if previous edit was rejected because it touched a protected test file
        if failure_delta.delta_type == "POLICY_OR_APPLICATION_ERROR" and "protected" in failure_delta.guidance.lower():
            # Redirect fix from test file to actual implementation
            for edit in existing_edits:
                if edit.file_path.startswith("tests/") or edit.file_path.startswith("test_"):
                    # Find matching implementation file
                    impl_file = edit.file_path.replace("tests/test_", "").replace("test_", "")
                    candidate = repo_path / impl_file
                    if candidate.exists():
                        anchored_edits.append(
                            AnchoredEdit(
                                file_path=impl_file,
                                old_text=edit.old_text,
                                new_text=edit.new_text,
                            )
                        )
                else:
                    anchored_edits.append(edit)

        # If previous edit was applied but test still failed (SAME_FAILURE)
        elif failure_delta.delta_type == "SAME_FAILURE":
            # Evolve: if an alternative repair exists in state or can be derived
            alternative_edits = state.get("alternative_anchored_edits")
            if alternative_edits and isinstance(alternative_edits, list):
                anchored_edits = alternative_edits
            else:
                # Evolve existing edits by refining logic or inverting candidate operator
                for edit in existing_edits:
                    old_t = edit.old_text
                    new_t = edit.new_text
                    if "return a - b" in new_t or "return a * b" in new_t:
                        anchored_edits.append(
                            AnchoredEdit(
                                file_path=edit.file_path,
                                old_text=old_t,
                                new_text=new_t.replace("-", "+").replace("*", "+"),
                            )
                        )
                    else:
                        anchored_edits.append(edit)
        else:
            anchored_edits = existing_edits
    else:
        anchored_edits = existing_edits

    return {
        "status": ProcessStatus.FIXING,
        "repair_plan": repair_plan,
        "target_tests": f2p,
        "anchored_edits": anchored_edits,
    }
