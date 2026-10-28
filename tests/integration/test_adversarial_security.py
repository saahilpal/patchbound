"""Adversarial Security Test Suite challenging sandboxing, path traversal, tampering, and credentials."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from patchbound.audit.journal import AuditJournal
from patchbound.cli.main import main
from patchbound.core.clone import CloneManager
from patchbound.core.models import (
    AnchoredEdit,
    ProcessStatus,
)
from patchbound.core.patcher import PatchApplicationError, Patcher
from patchbound.graph.workflow import compile_patchbound_graph


def test_path_traversal_in_anchored_edits_rejected() -> None:
    """Adversarial: Anchored edit with ../ or absolute paths must be rejected with PatchApplicationError."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "workspace"
        ws.mkdir()
        outside = Path(td) / "outside.txt"
        outside.write_text("secret sensitive line\n", encoding="utf-8")

        patcher = Patcher(ws)

        # 1. Relative path traversal
        edit_relative = AnchoredEdit(
            file_path="../outside.txt",
            old_text="secret",
            new_text="malicious",
        )
        with pytest.raises(
            PatchApplicationError, match="Path traversal detected|Cannot resolve target path"
        ):
            patcher.apply_edits([edit_relative])
        assert "secret sensitive line" in outside.read_text(encoding="utf-8")

        # 2. Absolute path traversal
        edit_abs = AnchoredEdit(
            file_path=str(outside.resolve()),
            old_text="secret",
            new_text="malicious",
        )
        with pytest.raises(PatchApplicationError, match="Absolute paths are forbidden"):
            patcher.apply_edits([edit_abs])
        assert "secret sensitive line" in outside.read_text(encoding="utf-8")


def test_symlink_traversal_in_anchored_edits_rejected() -> None:
    """Adversarial: Anchored edit targeting a symlink pointing outside workspace must be rejected."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "workspace"
        ws.mkdir()
        outside = Path(td) / "sensitive_config.env"
        outside.write_text("API_SECRET=super_secret_val\n", encoding="utf-8")

        # Create symlink inside workspace pointing outside
        symlink_target = ws / "evil_symlink.py"
        os.symlink(outside, symlink_target)

        patcher = Patcher(ws)
        edit = AnchoredEdit(
            file_path="evil_symlink.py",
            old_text="super_secret_val",
            new_text="corrupted_val",
        )
        with pytest.raises(PatchApplicationError, match="Refusing to write through symlink"):
            patcher.apply_edits([edit])

        # Assert outside file was untouched
        assert "API_SECRET=super_secret_val" in outside.read_text(encoding="utf-8")


def test_investigation_id_path_traversal_in_clone_manager() -> None:
    """Adversarial: Path traversal in investigation_id must be rejected to prevent arbitrary directory deletion."""
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td) / "scratch"
        scratch.mkdir()
        host = Path(td) / "host"
        host.mkdir()

        mgr = CloneManager(host, scratch)

        with pytest.raises(ValueError, match="Path traversal detected"):
            mgr.create_disposable_clone(investigation_id="../../../sensitive_dir", attempt=0)

        with pytest.raises(ValueError, match="Path traversal detected"):
            mgr.cleanup_attempt(investigation_id="../../../sensitive_dir", attempt=0)


def test_unapproved_patch_is_never_applied_to_host(tmp_path: Path) -> None:
    """Adversarial: A verified patch with human approval withheld MUST NEVER be applied to host."""
    repo_dir = tmp_path / "governance_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "tester@test.local"], cwd=repo_dir, check=True)

    calc_file = repo_dir / "calculator.py"
    calc_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    test_file = repo_dir / "tests" / "test_calc.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "from calculator import add\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8"
    )

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "repair",
            str(repo_dir),
            "--cmd",
            "pytest -v tests/test_calc.py",
            "--no-auto-approve",  # Human approval withheld!
            "--apply",  # User requested apply
        ],
    )
    assert result.exit_code == 0
    assert "Skipping host patch application: Patch has not been approved." in result.output

    # Invariant: Host code remains unchanged (buggy)
    assert "return a - b" in calc_file.read_text(encoding="utf-8")


def test_audit_journal_tampering_detection(tmp_path: Path) -> None:
    """Adversarial: Tampering with any entry in the audit journal is detected by SHA-256 verification."""
    journal_path = tmp_path / "audit.jsonl"
    aj = AuditJournal(journal_path)

    aj.record_event("EVENT_A", {"data": 1})
    aj.record_event("EVENT_B", {"data": 2})
    aj.record_event("EVENT_C", {"data": 3})

    # Initial state is valid
    is_valid, err = aj.verify_integrity()
    assert is_valid is True
    assert err is None

    # Attack 1: Modify payload of second record
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    import json

    record_dict = json.loads(lines[1])
    record_dict["payload"]["data"] = 9999
    lines[1] = json.dumps(record_dict)
    journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Invariant: Tampering detected
    is_valid, err = aj.verify_integrity()
    assert is_valid is False
    assert "Hash tampering detected" in str(err)

    # Attack 2: Delete second record (chain break)
    del lines[1]
    journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    is_valid, err = aj.verify_integrity()
    assert is_valid is False
    assert "Chain break at record #2" in str(err)


def test_host_integrity_preserved_on_rejected_repair(tmp_path: Path) -> None:
    """Adversarial: A failed or rejected repair leaves host repository 100% untouched."""
    repo_dir = tmp_path / "host_integrity_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "tester@test.local"], cwd=repo_dir, check=True)

    src = repo_dir / "app.py"
    src.write_text("def app():\n    return False\n", encoding="utf-8")
    tst = repo_dir / "tests" / "test_app.py"
    tst.parent.mkdir(parents=True, exist_ok=True)
    tst.write_text(
        "from app import app\ndef test_app():\n    assert app() is True\n", encoding="utf-8"
    )

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)

    clone_mgr = CloneManager(repo_dir, tmp_path / "scratch")
    pre_hash = clone_mgr.capture_host_state()

    app = compile_patchbound_graph()
    initial_state = {
        "investigation_id": f"integrity-{tmp_path.name}",
        "repo_path": str(repo_dir),
        "reproduce_cmd": ["pytest", "-v", "tests/test_app.py"],
        "attempt": 0,
        "max_attempts": 1,
        "status": ProcessStatus.INITIALIZING,
    }

    result = app.invoke(initial_state)
    assert result["status"] == ProcessStatus.TERMINATED

    # Invariant: Host state fingerprint is identical
    post_hash = clone_mgr.capture_host_state()
    assert pre_hash == post_hash
