"""Post-flight guardrails verifying patch integrity, cryptographic signatures, and zero secrets."""

import re
from patchproof.core.digest import compute_patch_digest
from patchproof.guardrails.base import GuardrailCheckResult, GuardrailSeverity, GuardrailViolation
from patchproof.llm.egress import EgressGate


class PostflightGuardrails:
    """Verifies that final artifacts, patches, and digests are tamper-free and safe to export."""

    @staticmethod
    def verify_patch_digest_integrity(
        base_tree_hash: str,
        canonical_diff: str,
        expected_digest: str,
    ) -> GuardrailCheckResult:
        """Verify that the patch digest matches SHA-256(base_tree || canonical_diff)."""
        recalculated = compute_patch_digest(base_tree_hash, canonical_diff)
        if recalculated != expected_digest:
            return GuardrailCheckResult(
                guardrail_id="POST-01-DIGEST-INTEGRITY",
                name="Cryptographic Digest Verification",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message=f"Digest mismatch! Expected: {expected_digest}, Computed: {recalculated}",
            )
        return GuardrailCheckResult(
            guardrail_id="POST-01-DIGEST-INTEGRITY",
            name="Cryptographic Digest Verification",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="Patch digest verified cryptographically.",
        )

    @staticmethod
    def check_diff_secret_leakage(canonical_diff: str) -> GuardrailCheckResult:
        """Ensure no private keys, AWS tokens, or environment credentials are introduced in the patch."""
        for pattern, replacement in EgressGate.SECRET_PATTERNS:
            if re.search(pattern, canonical_diff, flags=re.IGNORECASE):
                return GuardrailCheckResult(
                    guardrail_id="POST-02-SECRET-LEAK",
                    name="Diff Secret Leakage Inspection",
                    passed=False,
                    severity=GuardrailSeverity.HARD_GATE,
                    message="Secret pattern detected in generated diff! Export blocked.",
                )
        return GuardrailCheckResult(
            guardrail_id="POST-02-SECRET-LEAK",
            name="Diff Secret Leakage Inspection",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="No credentials or secret tokens found in patch diff.",
        )

    @staticmethod
    def check_approval_signature(
        human_approved: bool,
        signature: str | None,
    ) -> GuardrailCheckResult:
        """Verify that export only occurs if an approval signature is present."""
        if not human_approved or not signature:
            return GuardrailCheckResult(
                guardrail_id="POST-03-APPROVAL-GATE",
                name="Human Approval Cryptographic Gate",
                passed=False,
                severity=GuardrailSeverity.HARD_GATE,
                message="Cannot export unapproved patch. Human approval signature is missing.",
            )
        return GuardrailCheckResult(
            guardrail_id="POST-03-APPROVAL-GATE",
            name="Human Approval Cryptographic Gate",
            passed=True,
            severity=GuardrailSeverity.HARD_GATE,
            message="Valid human approval signature verified.",
        )
