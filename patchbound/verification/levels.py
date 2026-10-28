"""Verification levels and quality metrics evaluator."""

from patchbound.core.models import (
    VerificationFlags,
    VerificationLevel,
    VerificationRecord,
)
from patchbound.verification.parsers.base import ParsedReport


class VerificationEvaluator:
    """Evaluates test run results against formal verification criteria (V1 - V3)."""

    @staticmethod
    def evaluate(
        attempt: int,
        f2p_test_ids: set[str],
        p2p_test_ids: set[str],
        impacted_test_ids: set[str],
        baseline_report: ParsedReport,
        patched_report: ParsedReport,
        patch_digest: str,
        is_flake_checked: bool = False,
        is_pinned_clean: bool = True,
        is_policy_clean: bool = True,
    ) -> VerificationRecord:
        """Compute formal verification level and quality record."""
        # 1. Anti-zero-run and anti-skip checks
        if patched_report.total_executed < len(f2p_test_ids):
            # Not even the target tests ran
            level = VerificationLevel.V0_FAILED
        elif patched_report.total_skipped > baseline_report.total_skipped:
            # Tests were skipped/suppressed
            level = VerificationLevel.V0_FAILED
        else:
            # Check Fail-to-Pass (F2P) flipping
            passed_ids = set(patched_report.passed_test_ids)
            f2p_all_passed = f2p_test_ids.issubset(passed_ids)

            # Check Pass-to-Pass (P2P) regressions
            regressed_p2p = [t for t in p2p_test_ids if t not in passed_ids]

            # Check Impacted tests
            impacted_all_passed = (
                impacted_test_ids.issubset(passed_ids) if impacted_test_ids else True
            )

            if not f2p_all_passed:
                level = VerificationLevel.V0_FAILED
            elif regressed_p2p:
                level = VerificationLevel.V0_FAILED
            elif not impacted_all_passed:
                level = VerificationLevel.V1_TARGET
            elif patched_report.total_failed == 0:
                level = VerificationLevel.V3_CI_CLEAN
            else:
                level = VerificationLevel.V2_IMPACT

        f2p_passed = [t for t in f2p_test_ids if t in patched_report.passed_test_ids]
        f2p_failed = [t for t in f2p_test_ids if t not in patched_report.passed_test_ids]
        p2p_regressed = [t for t in p2p_test_ids if t not in patched_report.passed_test_ids]

        flags = VerificationFlags(
            flake_checked=is_flake_checked,
            pinned_tests=is_pinned_clean,
            policy_clean=is_policy_clean,
        )

        from patchbound.core.digest import compute_sha256

        verification_hash = compute_sha256(
            f"{attempt}:{level.value}:{patch_digest}:{len(f2p_passed)}:{len(p2p_regressed)}"
        )

        return VerificationRecord(
            attempt=attempt,
            level=level,
            flags=flags,
            f2p_executed=list(f2p_test_ids),
            f2p_passed=f2p_passed,
            f2p_failed=f2p_failed,
            p2p_regressed=p2p_regressed,
            total_executed=patched_report.total_executed,
            total_skipped=patched_report.total_skipped,
            patch_digest=patch_digest,
            verification_hash=verification_hash,
        )
