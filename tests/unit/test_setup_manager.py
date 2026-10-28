"""Unit tests for SetupManager and diagnostic checks."""

from pathlib import Path

from patchproof.cli.setup import SetupManager


def test_diagnostics_runs_cleanly() -> None:
    """Verify that run_diagnostics executes without error and returns all expected subsystem checks."""
    checks = SetupManager.run_diagnostics()
    assert len(checks) >= 7

    names = [c.name for c in checks]
    assert "Python Version (>= 3.11)" in names
    assert "uv Package Manager" in names
    assert "Git Version Control" in names
    assert "GitHub CLI (gh)" in names
    assert "Ephemeral Sandboxes & CAS" in names
    assert "Policy Governance (policy.yaml)" in names
    assert "AI Model Providers" in names


def test_initialize_defaults_in_temp_dir(tmp_path: Path) -> None:
    """Verify that initialize_defaults provisions policy.yaml, .env, and sandboxes."""
    res = SetupManager.initialize_defaults(tmp_path)
    assert "policy.yaml" in res["created_files"]
    assert ".env" in res["created_files"]
    assert ".env.example" in res["created_files"]

    assert (tmp_path / "policy.yaml").exists()
    assert (tmp_path / ".env").exists()

    content = (tmp_path / "policy.yaml").read_text(encoding="utf-8")
    assert "default-strict-v1.1" in content
    assert "pytest_skip" in content
