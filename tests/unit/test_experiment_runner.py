"""Unit tests for the interventional ExperimentRunner."""

from pathlib import Path

from patchproof.core.models import AnchoredEdit
from patchproof.ledger.experiment import ExperimentRunner, ExperimentStatus


def test_experiment_supported_when_probe_passes(temp_workspace: Path) -> None:
    # In temp_workspace, test_calculator.py fails because calculator.py has `return a - b`.
    # Hypothesis: If we intervene by returning a + b, test will pass.
    runner = ExperimentRunner()
    probe_edits = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="return a - b  # Bug: minus instead of plus",
            new_text="return a + b",
        )
    ]

    record = runner.run_intervention(
        experiment_id="EXP-001",
        workspace_path=temp_workspace,
        hypothesis="Bug is caused by subtraction operator instead of addition in calculator.py",
        prediction="Test test_add will pass when replacing '-' with '+'",
        probe_edits=probe_edits,
        test_command=["pytest", "tests/test_calculator.py"],
    )

    assert record.experiment_id == "EXP-001"
    assert record.status == ExperimentStatus.SUPPORTED
    assert "Intervention succeeded" in record.details


def test_experiment_refuted_when_probe_still_fails(temp_workspace: Path) -> None:
    # Re-introduce failure in temp_workspace
    calc_file = temp_workspace / "calculator.py"
    calc_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    runner = ExperimentRunner()
    # Flawed hypothesis intervention
    probe_edits = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="return a - b",
            new_text="return a * b",
        )
    ]

    record = runner.run_intervention(
        experiment_id="EXP-002",
        workspace_path=temp_workspace,
        hypothesis="Bug is caused by subtraction instead of multiplication",
        prediction="Test test_add will pass with multiplication",
        probe_edits=probe_edits,
        test_command=["pytest", "tests/test_calculator.py"],
    )

    assert record.experiment_id == "EXP-002"
    assert record.status == ExperimentStatus.REFUTED
    assert "Intervention failed" in record.details
