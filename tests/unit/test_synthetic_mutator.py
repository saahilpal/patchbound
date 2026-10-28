"""Unit tests for synthetic mutator bug injection."""

from pathlib import Path
from patchproof.eval.mutator import SyntheticMutator


def test_generate_candidate_mutations(temp_workspace: Path):
    mutator = SyntheticMutator(temp_workspace)
    candidates = mutator.generate_candidate_mutations("calculator.py")

    assert len(candidates) > 0
    # calculator.py contains `return a - b`
    found_minus_mutation = any(" - " in orig for orig, _ in candidates)
    assert found_minus_mutation


def test_inject_validated_bug_flips_test(temp_workspace: Path):
    # In temp_workspace, test_calculator.py expects add(2, 3) == 5.
    # calculator.py originally has `return a - b` (failing).
    # Let's fix calculator.py so it passes first!
    calc_file = temp_workspace / "calculator.py"
    calc_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    mutator = SyntheticMutator(temp_workspace)
    fixture = mutator.inject_validated_bug(
        fixture_id="synth-calc-001",
        target_rel_path="calculator.py",
        test_command=["pytest", "tests/test_calculator.py"],
    )

    assert fixture is not None
    assert fixture.fixture_id == "synth-calc-001"
    # Ensure calculator.py was cleanly restored
    assert calc_file.read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
