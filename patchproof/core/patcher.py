"""Anchored edit applier and canonical git diff synthesis."""

import subprocess
from pathlib import Path

from patchproof.core.digest import compute_patch_digest
from patchproof.core.models import AnchoredEdit


class PatchApplicationError(Exception):
    """Raised when an anchored edit cannot be applied cleanly."""
    pass


class Patcher:
    """Applies anchored edits and generates canonical git diffs."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path.resolve()

    def get_base_tree_hash(self) -> str:
        """Get the git tree hash of HEAD in the workspace."""
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=self.workspace_path,
            text=True,
        ).strip()

    def apply_edits(self, edits: list[AnchoredEdit]) -> tuple[str, str]:
        """Apply a sequence of anchored edits.

        Returns:
            Tuple of (canonical_diff, patch_digest).
        """
        for edit in edits:
            target_file = self.workspace_path / edit.file_path
            if not target_file.is_file():
                raise PatchApplicationError(f"Target file does not exist: {edit.file_path}")

            content = target_file.read_text(encoding="utf-8")
            matches = content.count(edit.old_text)

            if matches == 0:
                raise PatchApplicationError(
                    f"Anchor not found in {edit.file_path} for snippet:\n{edit.old_text[:100]}..."
                )
            if matches > 1:
                raise PatchApplicationError(
                    f"Ambiguous anchor in {edit.file_path}: found {matches} matches for snippet:\n{edit.old_text[:100]}..."
                )

            # Apply replacement
            new_content = content.replace(edit.old_text, edit.new_text, 1)
            target_file.write_text(new_content, encoding="utf-8")

        # Synthesize canonical git diff
        canonical_diff = subprocess.check_output(
            ["git", "diff", "--no-prefix", "-U3"],
            cwd=self.workspace_path,
            text=True,
        )

        base_tree_hash = self.get_base_tree_hash()
        patch_digest = compute_patch_digest(base_tree_hash, canonical_diff)

        return canonical_diff, patch_digest
