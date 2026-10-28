"""Central guardrail coordinator orchestrating safety checks across pipeline lifecycle."""

from pathlib import Path

from patchbound.core.models import AnchoredEdit
from patchbound.guardrails.base import GuardrailCheckResult, GuardrailSeverity, GuardrailViolation
from patchbound.guardrails.inflight import InflightGuardrails
from patchbound.guardrails.postflight import PostflightGuardrails
from patchbound.guardrails.preflight import PreflightGuardrails


class GuardrailEngine:
    """Coordinates lifecycle guardrails across preflight, inflight, and postflight stages."""

    def __init__(self) -> None:
        self.seen_diff_hashes: set[str] = set()
        self.audit_results: list[GuardrailCheckResult] = []

    def run_preflight(self, repo_path: Path, scratch_dir: Path) -> list[GuardrailCheckResult]:
        """Execute all preflight safety validations."""
        results = PreflightGuardrails.run_all(repo_path, scratch_dir)
        self.audit_results.extend(results)
        return results

    def run_inflight(
        self,
        edits: list[AnchoredEdit],
        current_diff: str,
        attempt: int,
        tokens_consumed: int,
    ) -> list[GuardrailCheckResult]:
        """Validate live candidate patch and resource bounds."""
        results = [
            InflightGuardrails.check_patch_proportionality(edits),
            InflightGuardrails.check_duplicate_candidate(current_diff, self.seen_diff_hashes),
            InflightGuardrails.check_token_velocity(attempt, tokens_consumed),
        ]

        from patchbound.core.digest import compute_sha256

        self.seen_diff_hashes.add(compute_sha256(current_diff.strip()))

        for r in results:
            self.audit_results.append(r)
            if not r.passed and r.severity == GuardrailSeverity.HARD_GATE:
                raise GuardrailViolation(r.guardrail_id, r.message, r.severity)

        return results

    def run_postflight(
        self,
        base_tree_hash: str,
        canonical_diff: str,
        expected_digest: str,
        human_approved: bool,
        approval_signature: str | None,
    ) -> list[GuardrailCheckResult]:
        """Execute post-flight export and secret safety checks."""
        results = [
            PostflightGuardrails.verify_patch_digest_integrity(
                base_tree_hash, canonical_diff, expected_digest
            ),
            PostflightGuardrails.check_diff_secret_leakage(canonical_diff),
            PostflightGuardrails.check_approval_signature(human_approved, approval_signature),
        ]

        for r in results:
            self.audit_results.append(r)
            if not r.passed and r.severity == GuardrailSeverity.HARD_GATE:
                raise GuardrailViolation(r.guardrail_id, r.message, r.severity)

        return results
