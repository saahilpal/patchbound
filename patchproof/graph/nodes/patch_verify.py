"""Stage 6: Patch Gate and Verify (Deterministic)."""

from pathlib import Path
from typing import Any

from patchproof.config import settings
from patchproof.core.anti_cheat import AntiCheatChecker
from patchproof.core.models import (
    FailureDelta,
    ProcessStatus,
    VerificationLevel,
)
from patchproof.core.patcher import Patcher
from patchproof.core.policy import PolicyEngine
from patchproof.graph.state import PatchProofState
from patchproof.verification.levels import VerificationEvaluator
from patchproof.verification.oracle import PinnedOracle
from patchproof.verification.parsers.base import ParsedReport
from patchproof.verification.runner import VerificationRunner


def patch_verify_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 6: Apply edits, run anti-cheat and policy checks, restore oracle, and verify."""
    investigation_id = str(state.get("investigation_id", "inv-001"))
    attempt = int(state.get("attempt", 0))
    workspace = settings.workspace_root / investigation_id / f"attempt-{attempt}"
    repo_path = Path(str(state.get("repo_path", ".")))
    if not workspace.exists():
        from patchproof.core.clone import CloneManager
        clone_mgr = CloneManager(repo_path, settings.workspace_root)
        workspace = clone_mgr.create_disposable_clone(investigation_id, attempt)

    edits = state.get("anchored_edits", [])
    raw_cmd = state.get("reproduce_cmd") or state.get("reproduce_command")
    reproduce_cmd: list[str] = [str(c) for c in raw_cmd] if isinstance(raw_cmd, list) else ["pytest", "-v"]

    policy_engine = PolicyEngine.load_from_file(settings.policy_file)
    patcher = Patcher(workspace)

    try:
        # 1. Apply edits and synthesize canonical diff
        canonical_diff, patch_digest = patcher.apply_edits(edits)

        # 2. Enforce policy and anti-cheat invariants
        modified_files = [e.file_path for e in edits]
        policy_engine.check_diff(canonical_diff, modified_files)
        AntiCheatChecker.check_assert_removal(canonical_diff)

        # 3. Restore and verify pinned test oracle
        oracle = PinnedOracle(workspace)
        oracle.restore_test_files_and_configs()
        oracle.verify_no_test_diffs()

        # 4. Execute verification tests
        runner = VerificationRunner()
        patched_report = runner.run_tests(workspace, reproduce_cmd, timeout_seconds=settings.timeout_seconds_per_test)

        # Construct baseline report
        baseline_report = ParsedReport(
            total_executed=len(state.get("f2p_test_ids", [])) + len(state.get("p2p_test_ids", [])),
            total_failed=len(state.get("f2p_test_ids", [])),
            total_passed=len(state.get("p2p_test_ids", [])),
            passed_test_ids=state.get("p2p_test_ids", []),
        )

        record = VerificationEvaluator.evaluate(
            attempt=attempt,
            f2p_test_ids=set(state.get("f2p_test_ids", [])),
            p2p_test_ids=set(state.get("p2p_test_ids", [])),
            impacted_test_ids=set(),
            baseline_report=baseline_report,
            patched_report=patched_report,
            patch_digest=patch_digest,
            is_flake_checked=True,
            is_pinned_clean=True,
            is_policy_clean=True,
        )

        failure_delta = None
        if record.level == VerificationLevel.V0_FAILED:
            failure_delta = FailureDelta(
                attempt=attempt,
                max_attempts=int(state.get("max_attempts", 2)),
                delta_type="SAME_FAILURE",
                guidance="Failing test still failed. Revisit causal hypothesis.",
            )

        return {
            "status": ProcessStatus.VERIFYING,
            "canonical_diff": canonical_diff,
            "patch_digest": patch_digest,
            "verification_record": record,
            "failure_delta": failure_delta,
            "attempt": attempt + 1,
        }

    except Exception as e:
        # On failure, increment attempt and create failure delta
        return {
            "status": ProcessStatus.VERIFYING,
            "attempt": attempt + 1,
            "failure_delta": FailureDelta(
                attempt=attempt,
                max_attempts=int(state.get("max_attempts", 2)),
                delta_type="POLICY_OR_APPLICATION_ERROR",
                guidance=f"Patch application or policy error: {e}",
            ),
        }
