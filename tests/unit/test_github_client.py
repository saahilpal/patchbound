"""Unit tests for GitHubClient and GitHub models."""

from unittest.mock import patch

from patchproof.github.client import GitHubClient
from patchproof.github.models import GitHubIssue


def test_github_issue_extracts_reproduction_hints() -> None:
    """Verify that reproduction commands are extracted from issue descriptions."""
    issue_body = """
    ## Bug Report
    Calculator subtracts instead of adding when called with negative integers.

    ### Reproduction Steps
    Run the following command:
    ```bash
    pytest -v tests/test_calculator.py
    ```
    Also fails on:
    `pytest tests/test_calc_extended.py`
    """
    hints = GitHubIssue.extract_reproduction_hints(issue_body)
    assert len(hints) >= 2
    assert "pytest -v tests/test_calculator.py" in hints
    assert "pytest tests/test_calc_extended.py" in hints


def test_format_pr_body_includes_audit_signatures() -> None:
    """Verify that the generated PR body contains cryptographic signatures and claim tables."""
    body = GitHubClient.format_pr_body(
        investigation_id="inv-gh-101",
        issue_number=42,
        verification_level="V3",
        patch_digest="a" * 64,
        approval_signature="b" * 64,
        claims_markdown="| `CLM-001` | `OBSERVED` | high | Test failed |",
    )
    assert "## 🛡️ PatchProof Automated Verified Repair" in body
    assert "> **Resolves:** #42" in body
    assert f"- **Patch Digest (SHA-256):** `{'a' * 64}`" in body
    assert f"- **Governance Signature:** `{'b' * 64}`" in body
    assert "| `CLM-001` | `OBSERVED` | high | Test failed |" in body


def test_fetch_issue_parses_json_output() -> None:
    """Verify that fetch_issue parses gh CLI JSON output cleanly."""
    client = GitHubClient()
    mock_json = """{
        "number": 105,
        "title": "Fix off-by-one in pagination",
        "body": "Run `pytest -v tests/test_page.py` to see failure",
        "author": {"login": "octocat"},
        "labels": [{"name": "bug"}, {"name": "priority:high"}],
        "state": "OPEN",
        "url": "https://github.com/octocat/repo/issues/105"
    }"""

    with patch("subprocess.check_output", return_value=mock_json):
        issue = client.fetch_issue("octocat/repo", 105)
        assert issue.number == 105
        assert issue.title == "Fix off-by-one in pagination"
        assert issue.author == "octocat"
        assert "bug" in issue.labels
        assert "priority:high" in issue.labels
        assert "pytest -v tests/test_page.py" in issue.reproduction_hints


def test_fetch_pr_parses_json_output() -> None:
    """Verify that fetch_pr parses gh CLI output cleanly."""
    client = GitHubClient()
    mock_json = """{
        "number": 204,
        "title": "feat: add caching layer",
        "body": "Adds Redis caching",
        "headRefName": "feat/cache",
        "baseRefName": "main",
        "url": "https://github.com/octocat/repo/pull/204",
        "author": {"login": "dev"}
    }"""

    with patch("subprocess.check_output", return_value=mock_json):
        pr = client.fetch_pr("octocat/repo", 204)
        assert pr.number == 204
        assert pr.head_branch == "feat/cache"
        assert pr.base_branch == "main"
        assert pr.author == "dev"
