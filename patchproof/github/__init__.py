"""GitHub integration package for PatchProof."""

from patchproof.github.client import GitHubClient, GitHubClientError
from patchproof.github.models import GitHubIssue, GitHubPullRequest

__all__ = ["GitHubClient", "GitHubClientError", "GitHubIssue", "GitHubPullRequest"]
