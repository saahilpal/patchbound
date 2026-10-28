"""Unit tests for the anchored edit patcher."""

from pathlib import Path

import pytest

from patchbound.core.models import AnchoredEdit
from patchbound.core.patcher import PatchApplicationError, Patcher


def test_anchored_edit_application(temp_workspace: Path) -> None:
    patcher = Patcher(temp_workspace)
    edits = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="return a - b  # Bug: minus instead of plus",
            new_text="return a + b",
        )
    ]

    canonical_diff, digest = patcher.apply_edits(edits)

    assert "+    return a + b" in canonical_diff
    assert "-    return a - b" in canonical_diff
    assert len(digest) == 64  # SHA-256


def test_missing_anchor_raises_error(temp_workspace: Path) -> None:
    patcher = Patcher(temp_workspace)
    edits = [
        AnchoredEdit(
            file_path="calculator.py",
            old_text="non_existent_snippet_xyz()",
            new_text="replacement()",
        )
    ]

    with pytest.raises(PatchApplicationError, match="Anchor not found"):
        patcher.apply_edits(edits)
