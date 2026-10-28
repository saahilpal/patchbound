"""End-to-End integration tests for Phase 1 Deterministic Spine across 3 real fixtures.

Milestone M1 Deliverables:
1. Python pytest failure fixture -> reproduction -> triage -> mock fix -> V3 verification -> export
2. JavaScript / TypeScript test fixture -> reproduction -> Jest log triage -> mock fix -> verification
3. Syntax / Linter violation fixture -> reproduction -> triage -> policy / anti-cheat enforcement -> clean diagnosis report
"""

import subprocess
from pathlib import Path

from patchbound.core.models import (
    AnchoredEdit,
    OutcomeResult,
    ProcessStatus,
    VerificationLevel,
)
from patchbound.graph.workflow import compile_patchbound_graph


def create_git_fixture(path: Path, files: dict[str, str]) -> Path:
    """Helper to initialize a git fixture repository with specific files."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["git", "init"], cwd=path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "PatchBound Tester"], cwd=path)
    subprocess.check_call(["git", "config", "user.email", "tester@patchbound.dev"], cwd=path)

    for rel_path, content in files.items():
        file_path = path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    subprocess.check_call(["git", "add", "."], cwd=path)
    subprocess.check_call(
        ["git", "commit", "-m", "Initial test fixture commit"],
        cwd=path,
        stdout=subprocess.DEVNULL,
    )
    return path


def test_spine_python_pytest_end_to_end(tmp_path: Path) -> None:
    """Fixture 1: Python pytest failure cured by deterministic anchored edit."""
    fixture_dir = tmp_path / "fixtures" / "python_pytest"
    files = {
        "calculator.py": "def add(a, b):\n    return a - b  # Bug: minus instead of plus\n",
        "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
    repo_path = create_git_fixture(fixture_dir, files)

    # Compile the 9-stage LangGraph
    app = compile_patchbound_graph()

    # Initial state with mock LLM fix for calculator
    mock_edits = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="return a - b  # Bug: minus instead of plus",
            new_text="return a + b",
        )
    ]

    investigation_id = f"test-spine-py-{tmp_path.name}"
    initial_state = {
        "investigation_id": investigation_id,
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_calculator.py"],
        "anchored_edits": mock_edits,
        "attempt": 0,
        "max_attempts": 2,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    assert result["status"] == ProcessStatus.TERMINATED
    assert result["outcome"] == OutcomeResult.VERIFIED_EXPORTED
    assert result["reproduce_classification"] == "reproduced"
    assert "tests/test_calculator.py::test_add" in result["f2p_test_ids"]

    # Verify cryptographic patch digest and record
    record = result.get("verification_record")
    assert record is not None
    assert record.level == VerificationLevel.V3_CI_CLEAN
    assert len(result["patch_digest"]) == 64
    assert "+    return a + b" in result["canonical_diff"]

    # Verify export report markdown
    report_md = result.get("final_report_markdown", "")
    assert "# PatchBound Investigation & Verification Report" in report_md
    assert result["patch_digest"] in report_md


def test_spine_jest_vitest_mock_fixture(tmp_path: Path) -> None:
    """Fixture 2: TypeScript / JS fixture with test runner script."""
    fixture_dir = tmp_path / "fixtures" / "typescript_vitest"
    # Create a small script that behaves like vitest/jest: exits 1 when buggy, exits 0 when fixed
    runner_script = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        "code = Path('src/math.js').read_text()\n"
        "if 'return a + b' in code:\n"
        "    print('PASS src/math.test.js')\n"
        "    sys.exit(0)\n"
        "else:\n"
        "    print('FAIL src/math.test.js: expected 5 but received -1')\n"
        "    sys.exit(1)\n"
    )

    files = {
        "src/math.js": "function add(a, b) {\n    return a - b;\n}\n",
        "run_tests.py": runner_script,
    }
    repo_path = create_git_fixture(fixture_dir, files)
    (repo_path / "run_tests.py").chmod(0o755)

    app = compile_patchbound_graph()

    mock_edits = [
        AnchoredEdit(
            file_path="src/math.js",
            old_text="return a - b;",
            new_text="return a + b;",
        )
    ]

    investigation_id = f"test-spine-ts-{tmp_path.name}"
    initial_state = {
        "investigation_id": investigation_id,
        "repo_path": str(repo_path),
        "reproduce_cmd": ["python3", "run_tests.py"],
        "anchored_edits": mock_edits,
        "attempt": 0,
        "max_attempts": 2,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    assert result["status"] == ProcessStatus.TERMINATED
    assert result["outcome"] == OutcomeResult.VERIFIED_EXPORTED
    assert result["reproduce_classification"] == "reproduced"
    assert len(result["patch_digest"]) == 64


def test_spine_policy_rejection_fixture(tmp_path: Path) -> None:
    """Fixture 3: Syntax or anti-cheat violation fixture rejected by deterministic policy gate."""
    fixture_dir = tmp_path / "fixtures" / "policy_violation"
    files = {
        "src/auth.py": "def authenticate(token):\n    assert token is not None\n    return True\n",
        "tests/test_auth.py": "from src.auth import authenticate\ndef test_auth():\n    assert authenticate(None) is False\n",
    }
    repo_path = create_git_fixture(fixture_dir, files)

    app = compile_patchbound_graph()

    # Cheating edit: attempts to delete an assertion
    cheating_edits = [
        AnchoredEdit(
            file_path="src/auth.py",
            old_text="assert token is not None\n    return True",
            new_text="return True",
        )
    ]

    investigation_id = f"test-spine-cheat-{tmp_path.name}"
    initial_state = {
        "investigation_id": investigation_id,
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_auth.py"],
        "anchored_edits": cheating_edits,
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    # Verification should catch the anti-cheat violation and terminate
    delta = result.get("failure_delta")
    assert delta is not None
    assert delta.delta_type == "POLICY_OR_APPLICATION_ERROR"
