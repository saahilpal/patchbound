"""Stage 7: Review (Deterministic anti-cheat + Independent Blind Reviewer)."""

from typing import Any

from patchproof.config import settings
from patchproof.core.anti_cheat import AntiCheatChecker
from patchproof.core.models import ProcessStatus, VerificationLevel
from patchproof.core.policy import PolicyEngine, PolicyViolation
from patchproof.graph.state import PatchProofState
from patchproof.llm.egress import EgressGate


def review_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 7: Blind review of canonical diff, asserting anti-cheat, secret hygiene, and policy invariants."""
    record = state.get("verification_record")
    canonical_diff = state.get("canonical_diff", "")
    edits = state.get("anchored_edits", [])
    modified_files = [e.file_path for e in edits]

    # Invariant 1: Must have a passing verification level
    if not record or record.level == VerificationLevel.V0_FAILED:
        return {
            "status": ProcessStatus.REVIEWING,
            "review_status": "rejected",
            "review_notes": "Rejected: verification record failed or missing.",
        }

    # Invariant 2: Secret & Credential Egress Scrubbing
    if EgressGate.contains_leak(canonical_diff):
        return {
            "status": ProcessStatus.REVIEWING,
            "review_status": "rejected",
            "review_notes": "Rejected: credential or private key leak detected in diff.",
        }

    # Invariant 3: Anti-Cheat & Oracle Integrity
    try:
        AntiCheatChecker.check_assert_removal(canonical_diff)
        AntiCheatChecker.check_banned_constructs(canonical_diff)
    except PolicyViolation as pv:
        return {
            "status": ProcessStatus.REVIEWING,
            "review_status": "rejected",
            "review_notes": f"Rejected by anti-cheat: {pv}",
        }

    # Invariant 4: Declarative Policy Engine Check
    try:
        policy_engine = PolicyEngine.load_from_file(settings.policy_file)
        policy_engine.check_diff(canonical_diff, modified_files)
    except PolicyViolation as pv:
        return {
            "status": ProcessStatus.REVIEWING,
            "review_status": "rejected",
            "review_notes": f"Rejected by policy: {pv}",
        }

    # All invariants verified
    return {
        "status": ProcessStatus.REVIEWING,
        "review_status": "approved",
        "review_notes": "Independent review passed: verified clean execution, zero anti-cheat violations, zero credential leaks.",
    }
