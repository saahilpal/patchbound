"""Grounding validator: mechanically checks citation integrity and quotes against git tree."""

import subprocess
from pathlib import Path

from patchbound.ledger.claim import ClaimItem


class CitationFabricationError(Exception):
    """Raised when an LLM citation quotes code that does not exist at the recorded tree hash."""

    pass


class GroundingValidator:
    """Validates citations in the Claim Ledger against true repository state."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path.resolve()

    def validate_claim(self, claim: ClaimItem) -> None:
        """Verify that every citation in the claim exists verbatim at the specified tree hash."""
        for citation in claim.citations:
            # Check if file exists at that tree/commit
            try:
                file_content = subprocess.check_output(
                    ["git", "cat-file", "-p", f"{citation.tree_hash}:{citation.file_path}"],
                    cwd=self.workspace_path,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                raise CitationFabricationError(
                    f"Fabricated file citation: {citation.file_path} does not exist at tree {citation.tree_hash}"
                ) from e

            lines = file_content.splitlines()
            start_idx = max(0, citation.line_start - 1)
            end_idx = min(len(lines), citation.line_end)
            actual_lines = lines[start_idx:end_idx]
            actual_text = "\n".join(actual_lines)

            # Check if quoted text matches reality
            norm_quote = citation.exact_quote.strip()
            norm_actual = actual_text.strip()

            if norm_quote not in norm_actual and norm_actual not in norm_quote:
                raise CitationFabricationError(
                    f"Fabricated code quote in {citation.file_path}:{citation.line_start}-{citation.line_end}.\n"
                    f"Cited: '{norm_quote}'\n"
                    f"Actual: '{norm_actual}'"
                )


# Alias for roadmap compatibility
CitationValidator = GroundingValidator
