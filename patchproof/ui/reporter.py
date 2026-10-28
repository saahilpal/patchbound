"""Markdown and JSON report generator for human and machine consumption."""

import json
from pathlib import Path
from typing import Any

from patchproof.core.models import VerificationRecord
from patchproof.ledger.claim import ClaimItem


class ReportGenerator:
    """Renders comprehensive, audited diagnosis and verification reports."""

    @staticmethod
    def render_markdown(
        investigation_id: str,
        repo_path: str,
        reproduce_cmd: str,
        outcome: str,
        record: VerificationRecord | None,
        claims: list[ClaimItem],
        canonical_diff: str | None,
        patch_digest: str | None,
    ) -> str:
        """Produce full GitHub Flavored Markdown investigation report."""
        level_str = record.level.value if record else "N/A"
        badge_color = "brightgreen" if level_str in ("V2", "V3") else "orange" if level_str == "V1" else "red"
        badge_md = f"![Verification Level](https://img.shields.io/badge/Verification_Level-{level_str}-{badge_color})"

        lines = [
            f"# PatchProof Autonomous Repair Report: `{investigation_id}`",
            "",
            f"{badge_md} ![Trust Boundary](https://img.shields.io/badge/Trust_Boundary-Deterministic_Spine-blue)",
            "",
            "## 1. Executive Summary",
            "",
            f"- **Repository:** `{repo_path}`",
            f"- **Reproduction Command:** `{reproduce_cmd}`",
            f"- **Outcome:** **`{outcome}`**",
            f"- **Verification Level:** **`{level_str}`**",
            f"- **Patch Digest:** `{patch_digest or 'N/A'}`",
            "",
        ]

        if record:
            lines.extend([
                "## 2. Verification Oracle Matrix",
                "",
                "| Metric | Target Set | Result |",
                "| :--- | :--- | :--- |",
                f"| **Fail-to-Pass (F2P)** | {len(record.f2p_executed)} tests | {len(record.f2p_passed)} flipped to PASSED |",
                f"| **Pass-to-Pass (P2P)** | Baseline passing | {len(record.p2p_regressed)} regressions |",
                f"| **Oracle Restoration** | Hashes pinned | {'PASSED' if record.flags.pinned_tests else 'FAILED'} |",
                f"| **Flake Check** | $N \\ge 3$ consecutive | {'PASSED' if record.flags.flake_checked else 'FAILED'} |",
                f"| **Policy Cleanliness** | AST Anti-Cheat | {'PASSED' if record.flags.policy_clean else 'FAILED'} |",
                "",
            ])

        if claims:
            lines.extend([
                "## 3. Cryptographic Claim Ledger",
                "",
                "| Claim ID | Type | Confidence | Statement | Evidence IDs |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for c in claims:
                ev_str = ", ".join(c.evidence_ids) if c.evidence_ids else "None"
                lines.append(f"| `{c.claim_id}` | `{c.claim_type.value}` | `{c.confidence}` | {c.statement} | `{ev_str}` |")
            lines.append("")

        if canonical_diff:
            lines.extend([
                "## 4. Canonical Patch Diff",
                "",
                "```diff",
                canonical_diff.strip(),
                "```",
                "",
            ])

        return "\n".join(lines)

    @staticmethod
    def export_json(
        export_path: Path,
        payload: dict[str, Any],
    ) -> None:
        """Write structured JSON audit record to disk."""
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
