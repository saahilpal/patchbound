"""Unit tests for verification levels evaluator."""

from patchproof.core.models import VerificationLevel
from patchproof.verification.levels import VerificationEvaluator
from patchproof.verification.parsers.base import ParsedReport


def test_level_v3_ci_clean():
    f2p = {"tests/test_foo.py::test_failing"}
    p2p = {"tests/test_foo.py::test_passing"}

    baseline = ParsedReport(
        total_executed=2,
        total_passed=1,
        total_failed=1,
        total_skipped=0,
        passed_test_ids=list(p2p),
    )

    patched = ParsedReport(
        total_executed=2,
        total_passed=2,
        total_failed=0,
        total_skipped=0,
        passed_test_ids=list(f2p | p2p),
    )

    record = VerificationEvaluator.evaluate(
        attempt=0,
        f2p_test_ids=f2p,
        p2p_test_ids=p2p,
        impacted_test_ids=set(),
        baseline_report=baseline,
        patched_report=patched,
        patch_digest="test_digest_123",
    )

    assert record.level == VerificationLevel.V3_CI_CLEAN
    assert record.flags.pinned_tests is True
    assert record.total_executed == 2


def test_level_v0_when_f2p_still_fails():
    f2p = {"tests/test_foo.py::test_failing"}
    p2p = {"tests/test_foo.py::test_passing"}

    baseline = ParsedReport(total_executed=2, total_passed=1, total_failed=1)
    patched = ParsedReport(
        total_executed=2,
        total_passed=1,
        total_failed=1,
        passed_test_ids=list(p2p),  # f2p did not pass
    )

    record = VerificationEvaluator.evaluate(
        attempt=0,
        f2p_test_ids=f2p,
        p2p_test_ids=p2p,
        impacted_test_ids=set(),
        baseline_report=baseline,
        patched_report=patched,
        patch_digest="test_digest_123",
    )

    assert record.level == VerificationLevel.V0_FAILED
