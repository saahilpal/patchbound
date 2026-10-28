"""End-to-End Product Validation Suite executing real repair scenarios in disposable repositories."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from patchbound.cli.main import main
from patchbound.core.models import (
    AnchoredEdit,
    OutcomeResult,
    ProcessStatus,
    VerificationLevel,
)
from patchbound.graph.nodes.investigator import _get_context_provider
from patchbound.graph.workflow import compile_patchbound_graph
from patchbound.llm.egress import EgressGate


def init_disposable_git_repo(repo_dir: Path, files: dict[str, str]) -> Path:
    """Helper to initialize a real git repository with given files and committed state."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "PatchBound QA"], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "qa@patchbound.internal"], cwd=repo_dir, check=True
    )

    for rel_path, content in files.items():
        fp = repo_dir / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True
    )
    return repo_dir


def test_scenario_1_deterministic_fix_and_cli_apply(tmp_path: Path) -> None:
    """Scenario 1 & 8: Real deterministic failing test, verified repair, and --apply to host."""
    repo_dir = tmp_path / "scenario_1_repo"
    files = {
        "calculator.py": "def add(a, b):\n    return a - b  # Bug\n",
        "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
    repo_path = init_disposable_git_repo(repo_dir, files)

    # 1. Verify host repo fails prior to repair
    safe_env = {**os.environ, "PYTHONPATH": str(repo_path)}
    pre_test = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/test_calculator.py"],
        cwd=repo_path,
        capture_output=True,
        env=safe_env,
    )
    assert pre_test.returncode != 0

    # 2. Run real CLI repair with --apply
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "repair",
            str(repo_path),
            "--cmd",
            f"{sys.executable} -m pytest -v tests/test_calculator.py",
            "--apply",
        ],
    )
    assert result.exit_code == 0
    assert "Verified patch successfully applied to host repository!" in result.output

    # 3. Verify host repo now genuinely PASSES tests after --apply
    post_test = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/test_calculator.py"],
        cwd=repo_path,
        capture_output=True,
        env=safe_env,
    )
    assert post_test.returncode == 0

    # 4. Verify host file was actually mutated to correct code
    updated_code = (repo_path / "calculator.py").read_text(encoding="utf-8")
    assert "return a + b" in updated_code


def test_scenario_2_failure_unrepairable_from_evidence(tmp_path: Path) -> None:
    """Scenario 2 & 7: Test with impossible assertion exits cleanly with BUDGET_EXHAUSTED."""
    repo_dir = tmp_path / "scenario_2_repo"
    files = {
        "dummy.py": "def dummy():\n    pass\n",
        "tests/test_impossible.py": "def test_impossible():\n    assert False is True\n",
    }
    repo_path = init_disposable_git_repo(repo_dir, files)

    app = compile_patchbound_graph()
    initial_state = {
        "investigation_id": f"scen2-{tmp_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_impossible.py"],
        "attempt": 0,
        "max_attempts": 2,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    assert result["status"] == ProcessStatus.TERMINATED
    assert result["outcome"] == OutcomeResult.BUDGET_EXHAUSTED
    assert result.get("verification_record") is not None
    assert result["verification_record"].level == VerificationLevel.V0_FAILED


def test_scenario_3_flaky_and_non_reproducible_early_exit(tmp_path: Path) -> None:
    """Scenario 3: Non-reproducible test exits immediately with NOT_REPRODUCIBLE and zero token spend."""
    repo_dir = tmp_path / "scenario_3_repo"
    files = {
        "tests/test_clean.py": "def test_already_passing():\n    assert 1 + 1 == 2\n",
    }
    repo_path = init_disposable_git_repo(repo_dir, files)

    app = compile_patchbound_graph()
    initial_state = {
        "investigation_id": f"scen3-{tmp_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_clean.py"],
        "attempt": 0,
        "max_attempts": 2,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    assert result["status"] == ProcessStatus.TERMINATED
    assert result["outcome"] == OutcomeResult.NOT_REPRODUCIBLE
    assert result["reproduce_classification"] == "not_reproducible"
    # Invariant: Never proceeded to fixer or verification
    assert "canonical_diff" not in result or result.get("canonical_diff") == ""


def test_scenario_4_regression_detection_and_rejection(tmp_path: Path) -> None:
    """Scenario 4: Proposed patch that fixes target test but breaks previously passing test is rejected."""
    repo_dir = tmp_path / "scenario_4_repo"
    files = {
        "math_utils.py": "def calc(x):\n    if x == 10:\n        return 0  # Bug for x=10\n    return x\n",
        "tests/test_math.py": (
            "from math_utils import calc\n\n"
            "def test_passing_one():\n    assert calc(5) == 5\n\n"
            "def test_passing_two():\n    assert calc(8) == 8\n\n"
            "def test_failing_target():\n    assert calc(10) == 10\n"
        ),
    }
    repo_path = init_disposable_git_repo(repo_dir, files)

    app = compile_patchbound_graph()

    # Regression patch: replaces entire calc with `return 10`, which fixes test_failing_target,
    # but causes test_passing_one and test_passing_two to regress!
    regression_edit = [
        AnchoredEdit(
            file_path="math_utils.py",
            old_text="def calc(x):\n    if x == 10:\n        return 0  # Bug for x=10\n    return x",
            new_text="def calc(x):\n    return 10",
        )
    ]

    initial_state = {
        "investigation_id": f"scen4-{tmp_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_math.py"],
        "anchored_edits": regression_edit,
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    # Invariant: Rejected as V0_FAILED due to P2P regression
    record = result.get("verification_record")
    assert record is not None
    assert record.level == VerificationLevel.V0_FAILED
    assert len(record.p2p_regressed) > 0
    assert (
        "test_passing_one" in record.p2p_regressed[0]
        or "test_passing_two" in record.p2p_regressed[0]
    )
    assert result["outcome"] == OutcomeResult.BUDGET_EXHAUSTED


def test_scenario_5_anti_cheat_test_tampering_rejection(tmp_path: Path) -> None:
    """Scenario 5: Attempted modification of test file to skip or fake pass is blocked and restored."""
    repo_dir = tmp_path / "scenario_5_repo"
    files = {
        "calculator.py": "def multiply(a, b):\n    return a + b  # Bug\n",
        "tests/test_calc.py": "from calculator import multiply\n\ndef test_mult():\n    assert multiply(2, 3) == 6\n",
    }
    repo_path = init_disposable_git_repo(repo_dir, files)

    app = compile_patchbound_graph()

    # Malicious edit: modifying the test file to skip or change assertion
    tampering_edit = [
        AnchoredEdit(
            file_path="tests/test_calc.py",
            old_text="    assert multiply(2, 3) == 6",
            new_text="    import pytest\n    pytest.skip('bypassed')",
        )
    ]

    initial_state = {
        "investigation_id": f"scen5-{tmp_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_calc.py"],
        "anchored_edits": tampering_edit,
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)

    # Invariant: Rejection recorded with policy violation guidance
    delta = result.get("failure_delta")
    assert delta is not None
    assert delta.delta_type == "POLICY_OR_APPLICATION_ERROR"
    assert "policy" in delta.guidance.lower() or "protected" in delta.guidance.lower()
    assert result["outcome"] == OutcomeResult.BUDGET_EXHAUSTED


def test_scenario_6_invalid_and_ambiguous_patch_rejection(tmp_path: Path) -> None:
    """Scenario 6: Edit with non-existent or ambiguous anchor is rejected cleanly."""
    repo_dir = tmp_path / "scenario_6_repo"
    files = {
        "service.py": "def run():\n    pass\n",
        "tests/test_service.py": "def test_run():\n    assert False\n",
    }
    repo_path = init_disposable_git_repo(repo_dir, files)

    app = compile_patchbound_graph()

    # Anchor that doesn't exist
    invalid_edit = [
        AnchoredEdit(
            file_path="service.py",
            old_text="NON_EXISTENT_ANCHOR_LINE",
            new_text="replacement",
        )
    ]

    initial_state = {
        "investigation_id": f"scen6-{tmp_path.name}",
        "repo_path": str(repo_path),
        "reproduce_cmd": ["pytest", "-v", "tests/test_service.py"],
        "anchored_edits": invalid_edit,
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    delta = result.get("failure_delta")
    assert delta is not None
    assert delta.delta_type == "POLICY_OR_APPLICATION_ERROR"
    assert "Anchor not found" in delta.guidance


def test_context_modes_auto_standard_and_explicit_synapse(tmp_path: Path) -> None:
    """Verify that context mode works for auto and standard, and fails cleanly on unindexed synapse."""
    clean_repo = tmp_path / "context_mode_repo"
    clean_repo.mkdir()

    # 1. Standard mode returns StandardContextProvider
    std_provider = _get_context_provider(clean_repo, mode="standard")
    assert std_provider.name == "StandardContextProvider"

    # 2. Auto mode on unindexed repo falls back cleanly to StandardContextProvider
    auto_provider = _get_context_provider(clean_repo, mode="auto")
    assert auto_provider.name == "StandardContextProvider"

    # 3. Explicit synapse mode on unindexed repo raises RuntimeError with clear remediation
    with pytest.raises(RuntimeError, match="not indexed by Synapse"):
        _get_context_provider(clean_repo, mode="synapse")


def test_egress_gate_ai_provider_key_redaction() -> None:
    """Verify that EgressGate sanitizes Anthropic, OpenAI, Gemini, and DeepSeek keys."""
    fake_ant = "sk-ant-api03-" + "abcdef1234567890123456789012"
    fake_oai = "sk-proj-" + "1234567890abcdef1234567890abcdef"
    fake_gem = "AIzaSy" + "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"
    fake_deep = "sk-" + "0" * 32
    prompt_with_secrets = (
        f"Here is my Anthropic key: {fake_ant} and "
        f"OpenAI key: {fake_oai} and "
        f"Gemini key: {fake_gem} and "
        f"DeepSeek key: {fake_deep}."
    )
    sanitized = EgressGate.sanitize_text(prompt_with_secrets)
    assert "sk-ant-api03" not in sanitized
    assert "[REDACTED_ANTHROPIC_KEY]" in sanitized
    assert "sk-proj-123456" not in sanitized
    assert "[REDACTED_OPENAI_KEY]" in sanitized
    assert "AIzaSy" not in sanitized
    assert "[REDACTED_GEMINI_KEY]" in sanitized
    assert fake_deep not in sanitized
    assert "[REDACTED_DEEPSEEK_KEY]" in sanitized
