"""In-flight guardrails monitoring execution state, loops, and resource velocity."""

from patchbound.core.digest import compute_sha256
from patchbound.core.models import AnchoredEdit
from patchbound.guardrails.base import GuardrailCheckResult, GuardrailSeverity


class InflightGuardrails:
    """Monitors live pipeline execution to catch thrashing, diff bloat, and infinite loops."""

    @staticmethod
    def check_duplicate_candidate(
        current_diff: str,
        seen_diff_hashes: set[str],
    ) -> GuardrailCheckResult:
        """Prevent thrashing on identical repeated candidate patches."""
        diff_hash = compute_sha256(current_diff.strip())
        if diff_hash in seen_diff_hashes:
            return GuardrailCheckResult(
                guardrail_id="INF-01-LOOP-DETECT",
                name="Duplicate Patch Loop Detection",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message="Candidate patch produces an identical diff to a previously rejected attempt.",
                details={"diff_hash": diff_hash},
            )
        return GuardrailCheckResult(
            guardrail_id="INF-01-LOOP-DETECT",
            name="Duplicate Patch Loop Detection",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="Patch diff is novel.",
        )

    @staticmethod
    def check_patch_proportionality(
        edits: list[AnchoredEdit],
        max_total_edits: int = 10,
        max_lines_per_edit: int = 150,
    ) -> GuardrailCheckResult:
        """Enforce surgical repair bounds: reject mass rewrites."""
        if len(edits) > max_total_edits:
            return GuardrailCheckResult(
                guardrail_id="INF-02-PATCH-SIZE",
                name="Patch Proportionality Check",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message=f"Too many distinct edits ({len(edits)} > max {max_total_edits}). Repair must be focused.",
            )

        for i, edit in enumerate(edits):
            added_lines = edit.new_text.count("\n") + 1
            if added_lines > max_lines_per_edit:
                return GuardrailCheckResult(
                    guardrail_id="INF-02-PATCH-SIZE",
                    name="Patch Proportionality Check",
                    passed=False,
                    severity=GuardrailSeverity.HARD_GATE,
                    message=f"Edit #{i + 1} on '{edit.file_path}' introduces {added_lines} lines (exceeds {max_lines_per_edit}).",
                    details={"file_path": edit.file_path, "lines": added_lines},
                )

        return GuardrailCheckResult(
            guardrail_id="INF-02-PATCH-SIZE",
            name="Patch Proportionality Check",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="Patch edit volume within proportionality bounds.",
        )

    @staticmethod
    def check_token_velocity(
        attempt: int,
        tokens_consumed: int,
        max_tokens_per_attempt: int = 50_000,
    ) -> GuardrailCheckResult:
        """Detect runaway token burn in agent loops."""
        if tokens_consumed > (attempt + 1) * max_tokens_per_attempt:
            return GuardrailCheckResult(
                guardrail_id="INF-03-TOKEN-VELOCITY",
                name="Token Velocity Guardrail",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message=f"Token consumption ({tokens_consumed}) exceeded budget for attempt {attempt}.",
            )
        return GuardrailCheckResult(
            guardrail_id="INF-03-TOKEN-VELOCITY",
            name="Token Velocity Guardrail",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="Token velocity within normal envelope.",
        )
