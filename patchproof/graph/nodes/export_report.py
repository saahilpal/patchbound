"""Stage 9: Export and Report (Deterministic)."""

from patchproof.core.models import OutcomeResult, ProcessStatus
from patchproof.graph.state import PatchProofState


def export_report_node(state: PatchProofState) -> dict:
    """Stage 9: Render diagnostic & verification report directly from the Claim Ledger."""
    investigation_id = state.get("investigation_id", "inv-001")
    record = state.get("verification_record")
    claims = state.get("claims", [])
    digest = state.get("patch_digest", "")

    report_lines = [
        f"# PatchProof Investigation & Verification Report: {investigation_id}",
        "",
        f"**Outcome:** Verified & Exported",
        f"**Verification Level:** {record.level.value if record else 'N/A'}",
        f"**Patch Digest:** `{digest}`",
        "",
        "## Claim Ledger",
    ]

    for c in claims:
        report_lines.append(f"- **[{c.claim_type.value.upper()}]** ({c.confidence} confidence): {c.statement}")

    report_md = "\n".join(report_lines)

    return {
        "status": ProcessStatus.TERMINATED,
        "outcome": OutcomeResult.VERIFIED_EXPORTED,
        "final_report_markdown": report_md,
    }
