"""Shared fixtures for PatchProof tests."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Fixture providing a clean temporary git repository workspace."""
    import subprocess

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    subprocess.check_call(["git", "init"], cwd=repo_dir, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "Test User"], cwd=repo_dir)
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=repo_dir)

    # Add initial file
    sample_file = repo_dir / "calculator.py"
    sample_file.write_text(
        "def add(a, b):\n    return a - b  # Bug: minus instead of plus\n",
        encoding="utf-8",
    )

    test_file = repo_dir / "tests" / "test_calculator.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    subprocess.check_call(["git", "add", "."], cwd=repo_dir)
    subprocess.check_call(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, stdout=subprocess.DEVNULL)

    return repo_dir
