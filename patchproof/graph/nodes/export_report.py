"""Stage 9: Export and Report (Deterministic Audit Trail & Report Generation)."""

from pathlib import Path
from typing import Any

from patchproof.audit.journal import AuditJournal
from patchproof.config import settings
from patchproof.core.models import OutcomeResult, ProcessStatus, VerificationLevel
from patchproof.graph.state import PatchProofState


def export_report_node(state: PatchProofState) -> dict[str, Any]:
    """Stage 9: Render diagnostic & verification report directly from the Claim Ledger and record in Audit Journal."""
    investigation_id = str(state.get("investigation_id", "inv-001"))
    record = state.get("verification_record")
    claims = state.get("claims", [])
    digest = str(state.get("patch_digest", ""))
    canonical_diff = state.get("canonical_diff", "")
    human_approved = state.get("human_approved", False)
    approval_signature = state.get("approval_signature", "")
    attempts = int(state.get("attempt", 0))
    repro_class = state.get("reproduce_classification", "reproduced")
    review_notes = state.get("review_notes", "N/A")

    # 1. Determine final outcome
    if human_approved and record and record.level != VerificationLevel.V0_FAILED:
        outcome = OutcomeResult.VERIFIED_EXPORTED
    elif record and record.level != VerificationLevel.V0_FAILED:
        outcome = OutcomeResult.VERIFIED_REJECTED
    elif repro_class == "flaky":
        outcome = OutcomeResult.FLAKY
    elif repro_class in ["not_reproducible", "env_mismatch"]:
        outcome = OutcomeResult.NOT_REPRODUCIBLE
    else:
        outcome = OutcomeResult.BUDGET_EXHAUSTED

    # 2. Write diff to export path if requested
    exported_path: str | None = None
    export_dest = state.get("export_path") or state.get("exported_patch_path")
    if canonical_diff and export_dest:
        dest_p = Path(str(export_dest))
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        dest_p.write_text(canonical_diff, encoding="utf-8")
        exported_path = str(dest_p)

    # 3. Log into Audit Journal
    journal = AuditJournal(settings.audit_journal_path)
    journal.record_event(
        event_type="PIPELINE_TERMINATED",
        payload={
            "investigation_id": investigation_id,
            "outcome": outcome.value,
            "verification_level": record.level.value if record else None,
            "patch_digest": digest,
            "approval_signature": approval_signature,
            "attempts": attempts,
            "claims_count": len(claims),
        },
    )

    # 4. Construct Markdown Diagnostic Report
    report_lines = [
        f"# PatchProof Investigation & Verification Report: `{investigation_id}`",
        "",
        f"**Outcome:** `{outcome.value}`  ",
        f"**Verification Level:** `{record.level.value if record else 'N/A'}`  ",
        f"**Attempts Used:** `{attempts}`  ",
        f"**Patch Digest:** `{digest or 'None'}`  ",
        f"**Approval Signature:** `{approval_signature or 'Unsigned'}`  ",
        f"**Review Notes:** {review_notes}",
        "",
        "## Epistemological Claim Ledger",
        "",
        "| Claim ID | Category | Confidence | Statement |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for c in claims:
        badge = f"`{c.claim_type.value.upper()}`"
        report_lines.append(f"| `{c.claim_id}` | {badge} | {c.confidence} | {c.statement} |")

    if canonical_diff:
        report_lines.extend([
            "",
            "## Canonical Patch Diff",
            "```diff",
            canonical_diff.strip(),
            "```",
        ])

    report_md = "\n".join(report_lines)

    return {
        "status": ProcessStatus.TERMINATED,
        "outcome": outcome,
        "final_report_markdown": report_md,
        "exported_patch_path": exported_path,
    }
