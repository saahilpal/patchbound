"""GitHub integration package for PatchBound."""

from patchbound.github.client import GitHubClient, GitHubClientError
from patchbound.github.models import GitHubIssue, GitHubPullRequest

__all__ = ["GitHubClient", "GitHubClientError", "GitHubIssue", "GitHubPullRequest"]
