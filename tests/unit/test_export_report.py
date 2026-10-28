"""Unit tests for Stage 9 Export Report node outcome handling."""

from patchbound.core.models import (
    OutcomeResult,
    ProcessStatus,
    VerificationFlags,
    VerificationLevel,
    VerificationRecord,
)
from patchbound.graph.nodes.export_report import export_report_node
from patchbound.graph.state import PatchBoundState


def test_export_report_preserves_explicit_diagnosis_only_outcome() -> None:
    """Verify that export_report_node preserves OutcomeResult.DIAGNOSIS_ONLY without overriding."""
    state: PatchBoundState = {
        "investigation_id": "inv-test-diag",
        "outcome": OutcomeResult.DIAGNOSIS_ONLY,
        "status": ProcessStatus.TERMINATED,
        "reproduce_classification": "reproduced",
        "attempt": 0,
        "claims": [],
    }
    result = export_report_node(state)
    assert result["outcome"] == OutcomeResult.DIAGNOSIS_ONLY
    assert "**Outcome:** `diagnosis_only`" in result["final_report_markdown"]


def test_export_report_preserves_flaky_and_not_reproducible() -> None:
    """Verify that export_report_node respects flaky and not_reproducible classifications."""
    state_flaky: PatchBoundState = {
        "investigation_id": "inv-flaky",
        "reproduce_classification": "flaky",
        "attempt": 0,
        "claims": [],
    }
    res_flaky = export_report_node(state_flaky)
    assert res_flaky["outcome"] == OutcomeResult.FLAKY

    state_not_repro: PatchBoundState = {
        "investigation_id": "inv-not-repro",
        "reproduce_classification": "not_reproducible",
        "attempt": 0,
        "claims": [],
    }
    res_not_repro = export_report_node(state_not_repro)
    assert res_not_repro["outcome"] == OutcomeResult.NOT_REPRODUCIBLE


def test_export_report_verified_exported_outcome() -> None:
    """Verify that human approval + non-V0 record produces VERIFIED_EXPORTED."""
    record = VerificationRecord(
        attempt=0,
        level=VerificationLevel.V3_CI_CLEAN,
        flags=VerificationFlags(flake_checked=True, pinned_tests=True, policy_clean=True),
        f2p_passed=["test_one"],
        total_executed=5,
    )
    state: PatchBoundState = {
        "investigation_id": "inv-verified",
        "verification_record": record,
        "human_approved": True,
        "approval_signature": "SIG-12345",
        "patch_digest": "DIGEST-ABCDE",
        "attempt": 1,
        "claims": [],
    }
    res = export_report_node(state)
    assert res["outcome"] == OutcomeResult.VERIFIED_EXPORTED
    assert "verified_exported" in res["final_report_markdown"]
