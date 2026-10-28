"""Data models for GitHub integration: issues, pull requests, and review comments."""

import re

from pydantic import BaseModel, Field


class GitHubIssue(BaseModel):
    """Structured representation of a GitHub issue."""

    number: int
    title: str
    body: str
    author: str
    labels: list[str] = Field(default_factory=list)
    state: str = "open"
    url: str
    reproduction_hints: list[str] = Field(default_factory=list)

    @classmethod
    def extract_reproduction_hints(cls, body: str) -> list[str]:
        """Extract test commands or error traces mentioned in the issue body."""
        hints: list[str] = []
        # Find test commands like `pytest tests/test_foo.py` or `npm test`
        cmd_matches = re.findall(r"(?:pytest|npm test|cargo test|go test)\s+[^\n`]+", body)
        hints.extend([m.strip() for m in cmd_matches])

        # Find code blocks marked bash/sh/python
        fenced_blocks = re.findall(r"```(?:bash|sh|console)?\n([\s\S]+?)```", body)
        for block in fenced_blocks:
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith(("pytest", "python -m unittest", "cargo test", "npm test")):
                    hints.append(stripped)

        return list(dict.fromkeys(hints))  # Deduplicate preserving order


class GitHubPullRequest(BaseModel):
    """Structured representation of a GitHub pull request."""

    number: int
    title: str
    body: str
    head_branch: str
    base_branch: str = "main"
    url: str
    diff_url: str = ""
    author: str = ""
