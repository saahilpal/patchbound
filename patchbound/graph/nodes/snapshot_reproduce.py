"""Stage 1: Snapshot and Reproduce (Deterministic)."""

from pathlib import Path
from typing import Any

from patchbound.config import settings
from patchbound.core.clone import CloneManager
from patchbound.core.models import ProcessStatus
from patchbound.graph.state import PatchBoundState
from patchbound.verification.runner import VerificationRunner


def snapshot_reproduce_node(state: PatchBoundState) -> dict[str, Any]:
    """Stage 1: Create disposable clone and execute reproduction baseline N times."""
    investigation_id = str(state.get("investigation_id", "inv-001"))
    repo_path = Path(str(state.get("repo_path", ".")))
    raw_cmd = state.get("reproduce_cmd") or state.get("reproduce_command")
    reproduce_cmd: list[str] = (
        [str(c) for c in raw_cmd] if isinstance(raw_cmd, list) else ["pytest", "-v"]
    )
    attempt = int(state.get("attempt", 0))

    clone_mgr = CloneManager(repo_path, settings.workspace_root)
    clone_mgr.record_pre_state()
    workspace = clone_mgr.create_disposable_clone(investigation_id, attempt)

    runner = VerificationRunner()
    runs = []
    num_runs = 3

    for _ in range(num_runs):
        parsed = runner.run_tests(
            workspace, reproduce_cmd, timeout_seconds=settings.timeout_seconds_per_test
        )
        runs.append(parsed)

    # Classify reproduction
    failed_counts = [r.total_failed for r in runs]
    if all(c == 0 for c in failed_counts):
        classification = "not_reproducible"
    elif all(c > 0 for c in failed_counts):
        classification = "reproduced"
    else:
        classification = "flaky"

    # Identify F2P (failed in runs) and P2P (passed in runs)
    baseline_run = runs[0]
    f2p = [sig.test_id for sig in baseline_run.failed_signatures]
    p2p = baseline_run.passed_test_ids

    return {
        "status": ProcessStatus.REPRODUCING,
        "reproduce_classification": classification,
        "f2p_test_ids": f2p,
        "p2p_test_ids": p2p,
        "failure_signatures": baseline_run.failed_signatures,
        "active_failure_signature": baseline_run.failed_signatures[0]
        if baseline_run.failed_signatures
        else None,
    }
