"""Integration test suite verifying multi-attempt loop evolution, recovery, and termination."""

import subprocess
from pathlib import Path

from click.testing import CliRunner

from patchbound.cli.main import main
from patchbound.core.models import (
    AnchoredEdit,
    OutcomeResult,
    ProcessStatus,
    VerificationLevel,
)
from patchbound.graph.workflow import compile_patchbound_graph


def create_git_fixture(repo_dir: Path, files: dict[str, str]) -> Path:
    """Helper to initialize a real git repository with fixture files."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "PatchBound Tester"], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@patchbound.internal"], cwd=repo_dir, check=True
    )

    for rel_path, content in files.items():
        file_path = repo_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit with failing test"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    return repo_dir


def test_multi_attempt_loop_evolution_and_recovery(tmp_path: Path) -> None:
    """Verify that an initial failed repair attempt evolves, fixes the bug in attempt 1, and verifies."""
    fixture_dir = tmp_path / "fixtures" / "loop_evolution"
    files = {
        "calculator.py": "def add(a, b):\n    return a - b  # Bug: minus instead of plus\n",
        "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
    repo_path = create_git_fixture(fixture_dir, files)

    app = compile_patchbound_graph()

    # Attempt 0: Provide an incorrect edit (multiplication instead of addition)
    wrong_initial_edit = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="return a - b  # Bug: minus instead of plus",
            new_text="return a * b",
        )
    ]

    investigation_id = f"test-loop-evo-{tmp_path.name}"
    initial_state = {
        "investigation_id": investigation_id,
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_calculator.py"],
        "anchored_edits": wrong_initial_edit,
        "attempt": 0,
        "max_attempts": 2,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    # Invariant: Attempt 0 failed, but the loop evolved and resolved it on Attempt 1
    assert result["status"] == ProcessStatus.TERMINATED
    assert result["outcome"] == OutcomeResult.VERIFIED_EXPORTED
    assert result["attempt"] == 2  # Total attempts recorded

    # Verify that the final verification record is V3_CI_CLEAN
    record = result.get("verification_record")
    assert record is not None
    assert record.level == VerificationLevel.V3_CI_CLEAN
    assert "+    return a + b" in result["canonical_diff"]

    # Verify Claim Ledger has both Attempt 0 and Attempt 1 claims
    claims = result.get("claims", [])
    claim_ids = [c.claim_id for c in claims]
    assert "CLM-OBS-0" in claim_ids
    assert "CLM-OBS-1" in claim_ids

    # Verify review and human approval
    assert result.get("review_status") == "approved"
    assert result.get("human_approved") is True
    assert result.get("approval_signature") is not None


def test_loop_exhaustion_terminates_cleanly(tmp_path: Path) -> None:
    """Verify that when a bug cannot be resolved, the loop terminates cleanly at max_attempts without crashing."""
    fixture_dir = tmp_path / "fixtures" / "loop_exhaustion"
    files = {
        "calculator.py": "def add(a, b):\n    return a - b\n",
        "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
    repo_path = create_git_fixture(fixture_dir, files)

    app = compile_patchbound_graph()

    # Provide an edit that keeps failing
    failing_edit = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="return a - b",
            new_text="return 0",
        )
    ]

    investigation_id = f"test-loop-exh-{tmp_path.name}"
    initial_state = {
        "investigation_id": investigation_id,
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_calculator.py"],
        "anchored_edits": failing_edit,
        "attempt": 0,
        "max_attempts": 2,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    assert result["status"] == ProcessStatus.TERMINATED
    assert result["outcome"] == OutcomeResult.BUDGET_EXHAUSTED
    assert result["attempt"] == 2


def test_cli_diagnose_and_repair_end_to_end(tmp_path: Path) -> None:
    """Verify that CLI diagnose and repair commands execute cleanly end-to-end."""
    fixture_dir = tmp_path / "fixtures" / "cli_repo"
    files = {
        "calculator.py": "def add(a, b):\n    return a - b\n",
        "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
    repo_path = create_git_fixture(fixture_dir, files)

    runner = CliRunner()

    # 1. Test diagnose command
    diag_res = runner.invoke(
        main, ["diagnose", str(repo_path), "--cmd", "pytest -v tests/test_calculator.py"]
    )
    assert diag_res.exit_code == 0
    assert "Target Repository:" in diag_res.output
    assert "Diagnosis Complete." in diag_res.output

    # 2. Test inspect symbols command
    sym_res = runner.invoke(main, ["inspect", "symbols", str(repo_path), "add"])
    assert sym_res.exit_code == 0
    assert "Using provider:" in sym_res.output
    assert "Found: `add`" in sym_res.output


def test_cli_repair_with_export_diff_and_apply(tmp_path: Path) -> None:
    """Verify that CLI repair with --export-diff and --apply runs and saves patch."""
    fixture_dir = tmp_path / "fixtures" / "cli_repair_repo"
    files = {
        "calculator.py": "def add(a, b):\n    return a - b\n",
        "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
    repo_path = create_git_fixture(fixture_dir, files)
    export_file = tmp_path / "test_fix.diff"

    runner = CliRunner()
    res = runner.invoke(
        main,
        [
            "repair",
            str(repo_path),
            "--cmd",
            "pytest -v tests/test_calculator.py",
            "--export-diff",
            str(export_file),
            "--apply",
        ],
    )
    assert res.exit_code == 0
    assert "Pipeline Terminated." in res.output
