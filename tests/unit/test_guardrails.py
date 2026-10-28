"""Unit tests for preflight, inflight, and postflight guardrails."""

from pathlib import Path

from patchbound.core.models import AnchoredEdit
from patchbound.guardrails.base import GuardrailSeverity
from patchbound.guardrails.inflight import InflightGuardrails
from patchbound.guardrails.postflight import PostflightGuardrails
from patchbound.guardrails.preflight import PreflightGuardrails


def test_preflight_valid_repo(temp_workspace: Path, tmp_path: Path) -> None:
    scratch_dir = tmp_path / "scratch"
    results = PreflightGuardrails.run_all(temp_workspace, scratch_dir)
    assert all(r.passed for r in results)


def test_preflight_invalid_repo(tmp_path: Path) -> None:
    fake_dir = tmp_path / "not_a_repo"
    fake_dir.mkdir()
    res = PreflightGuardrails.check_is_git_repository(fake_dir)
    assert not res.passed
    assert res.severity == GuardrailSeverity.HARD_GATE


def test_inflight_duplicate_detection() -> None:
    seen: set[str] = set()
    diff = "--- a/foo.py\n+++ b/foo.py\n+x = 1\n"

    r1 = InflightGuardrails.check_duplicate_candidate(diff, seen)
    assert r1.passed

    from patchbound.core.digest import compute_sha256

    seen.add(compute_sha256(diff.strip()))

    r2 = InflightGuardrails.check_duplicate_candidate(diff, seen)
    assert not r2.passed
    assert r2.severity == GuardrailSeverity.HARD_GATE


def test_inflight_patch_proportionality() -> None:
    normal_edits = [
        AnchoredEdit(file_path="a.py", old_text="x = 1", new_text="x = 2"),
        AnchoredEdit(file_path="b.py", old_text="y = 1", new_text="y = 2"),
    ]
    res = InflightGuardrails.check_patch_proportionality(normal_edits)
    assert res.passed

    # Too many edits
    excessive_edits = [
        AnchoredEdit(file_path=f"file_{i}.py", old_text="a", new_text="b") for i in range(15)
    ]
    res_excess = InflightGuardrails.check_patch_proportionality(excessive_edits, max_total_edits=10)
    assert not res_excess.passed


def test_postflight_secret_leak_detection() -> None:
    clean_diff = "--- a/file.py\n+++ b/file.py\n+x = 42\n"
    res_clean = PostflightGuardrails.check_diff_secret_leakage(clean_diff)
    assert res_clean.passed

    leaky_diff = "--- a/file.py\n+++ b/file.py\n+aws_key = 'AKIAIOSFODNN7EXAMPLE'\n"
    res_leak = PostflightGuardrails.check_diff_secret_leakage(leaky_diff)
    assert not res_leak.passed
    assert res_leak.severity == GuardrailSeverity.HARD_GATE


def test_postflight_digest_integrity() -> None:
    base_tree = "tree_hash_123"
    diff = "--- a/file.py\n+++ b/file.py\n+print(1)\n"
    from patchbound.core.digest import compute_patch_digest

    digest = compute_patch_digest(base_tree, diff)

    valid_res = PostflightGuardrails.verify_patch_digest_integrity(base_tree, diff, digest)
    assert valid_res.passed

    tampered_res = PostflightGuardrails.verify_patch_digest_integrity(
        base_tree, diff, "tampered_digest"
    )
    assert not tampered_res.passed
