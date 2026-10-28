"""Unit tests for the cryptographic Claim Ledger and Citation Validator."""

import subprocess
from pathlib import Path

import pytest

from patchproof.ledger.claim import ClaimItem, ClaimType, CodeCitation
from patchproof.ledger.validator import CitationFabricationError, CitationValidator


def test_valid_citation_passes_validation(temp_workspace: Path) -> None:
    # Get current commit hash (tree hash)
    commit_hash = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=temp_workspace, text=True)
        .strip()
    )

    # In temp_workspace, calculator.py line 2 has: "    return a - b  # Bug: minus instead of plus"
    citation = CodeCitation(
        file_path="calculator.py",
        line_start=1,
        line_end=2,
        tree_hash=commit_hash,
        exact_quote="return a - b",
    )

    claim = ClaimItem(
        claim_id="CLM-001",
        claim_type=ClaimType.OBSERVED,
        statement="Calculator subtraction operator used instead of addition.",
        citations=[citation],
    )

    validator = CitationValidator(temp_workspace)
    # Should pass without raising CitationFabricationError
    validator.validate_claim(claim)


def test_fabricated_file_path_raises_error(temp_workspace: Path) -> None:
    commit_hash = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=temp_workspace, text=True)
        .strip()
    )

    fabricated_citation = CodeCitation(
        file_path="non_existent_module.py",
        line_start=1,
        line_end=5,
        tree_hash=commit_hash,
        exact_quote="def hallucinated_function():",
    )

    claim = ClaimItem(
        claim_id="CLM-002",
        claim_type=ClaimType.INFERRED,
        statement="Hallucinated file citation.",
        citations=[fabricated_citation],
    )

    validator = CitationValidator(temp_workspace)
    with pytest.raises(CitationFabricationError, match="Fabricated file citation"):
        validator.validate_claim(claim)


def test_fabricated_quote_raises_error(temp_workspace: Path) -> None:
    commit_hash = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=temp_workspace, text=True)
        .strip()
    )

    # Valid file but quote does not match lines
    hallucinated_quote = CodeCitation(
        file_path="calculator.py",
        line_start=1,
        line_end=2,
        tree_hash=commit_hash,
        exact_quote="this code does not exist in lines 1-2",
    )

    claim = ClaimItem(
        claim_id="CLM-003",
        claim_type=ClaimType.INFERRED,
        statement="Hallucinated code quote.",
        citations=[hallucinated_quote],
    )

    validator = CitationValidator(temp_workspace)
    with pytest.raises(CitationFabricationError, match="Fabricated code quote"):
        validator.validate_claim(claim)
