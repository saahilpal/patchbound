"""Unit tests for PinnedOracle restoring protected files and preventing oracle tampering."""

import subprocess
from pathlib import Path

import pytest

from patchproof.core.policy import PolicyEngine, PolicyViolation
from patchproof.verification.oracle import PinnedOracle


def test_pinned_oracle_restores_nested_test_file(tmp_path: Path) -> None:
    """Verify that PinnedOracle restores test files in subdirectories matching policy."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@patchproof.internal"], cwd=repo_dir, check=True)

    test_file = repo_dir / "src" / "tests" / "test_math.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_one(): assert 1 == 1\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)

    # Mutate the test file (simulating a cheating agent)
    test_file.write_text("def test_one(): pass # Tampered\n", encoding="utf-8")

    oracle = PinnedOracle(repo_dir, policy_engine=PolicyEngine())
    oracle.restore_test_files_and_configs()

    # Verify the test was restored to original content
    assert test_file.read_text(encoding="utf-8") == "def test_one(): assert 1 == 1\n"
    # Should not raise PolicyViolation
    oracle.verify_no_test_diffs()


def test_pinned_oracle_tampering_detection(tmp_path: Path) -> None:
    """Verify that verify_no_test_diffs raises PolicyViolation if protected file was committed or remains dirty."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@patchproof.internal"], cwd=repo_dir, check=True)

    cfg = repo_dir / "pytest.ini"
    cfg.write_text("[pytest]\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)

    # Mutate cfg
    cfg.write_text("[pytest]\naddopts = --skip\n", encoding="utf-8")

    oracle = PinnedOracle(repo_dir, policy_engine=PolicyEngine())
    with pytest.raises(PolicyViolation, match="Oracle tampering detected"):
        oracle.verify_no_test_diffs()

