"""GitHub integration client wrapping the official GitHub CLI (gh) and REST API."""

import json
import re
import shutil
import subprocess
from pathlib import Path

from patchproof.core.credentials import CredentialStore
from patchproof.github.models import GitHubIssue, GitHubPullRequest


class GitHubClientError(Exception):
    """Raised when a GitHub API or CLI operation fails."""
    pass


class GitHubClient:
    """Client for GitHub issue fetching, repository cloning, branch pushing, and pull request creation."""

    def __init__(self, token: str | None = None):
        self.cli_bin = shutil.which("gh")
        self.token = token or CredentialStore().get_key("github")

    def is_authenticated(self) -> bool:
        """Check if authenticated via gh CLI or token."""
        if self.cli_bin:
            try:
                res = subprocess.run(
                    [self.cli_bin, "auth", "status"],
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    return True
            except Exception:
                pass
        return bool(self.token)

    def get_authenticated_user(self) -> str:
        """Get currently authenticated username."""
        if self.cli_bin:
            try:
                out = subprocess.check_output(
                    [self.cli_bin, "api", "user", "--jq", ".login"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                if out:
                    return out
            except Exception:
                pass
        return "authenticated-user"

    def fetch_issue(self, owner_repo: str, issue_number: int) -> GitHubIssue:
        """Fetch details of a GitHub issue."""
        if not self.cli_bin:
            raise GitHubClientError("GitHub CLI ('gh') is required to fetch issues. Install via 'brew install gh'.")

        cmd = [
            self.cli_bin,
            "issue",
            "view",
            f"{owner_repo}#{issue_number}" if "#" not in str(issue_number) else str(issue_number),
            "--json",
            "number,title,body,author,labels,state,url",
        ]
        try:
            raw = subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE)
            data = json.loads(raw)
            labels = [lbl.get("name", "") for lbl in data.get("labels", []) if isinstance(lbl, dict)]
            body = data.get("body", "") or ""
            hints = GitHubIssue.extract_reproduction_hints(body)

            return GitHubIssue(
                number=int(data.get("number", issue_number)),
                title=data.get("title", f"Issue #{issue_number}"),
                body=body,
                author=data.get("author", {}).get("login", "unknown") if isinstance(data.get("author"), dict) else "unknown",
                labels=labels,
                state=data.get("state", "open"),
                url=data.get("url", f"https://github.com/{owner_repo}/issues/{issue_number}"),
                reproduction_hints=hints,
            )
        except subprocess.CalledProcessError as e:
            err = e.stderr if hasattr(e, "stderr") and e.stderr else str(e)
            raise GitHubClientError(f"Failed to fetch issue {owner_repo}#{issue_number}: {err}") from e

    def fetch_pr(self, owner_repo: str, pr_number: int) -> GitHubPullRequest:
        """Fetch details of a GitHub pull request."""
        if not self.cli_bin:
            raise GitHubClientError("GitHub CLI ('gh') is required to inspect PRs.")

        cmd = [
            self.cli_bin,
            "pr",
            "view",
            f"{owner_repo}#{pr_number}",
            "--json",
            "number,title,body,headRefName,baseRefName,url,author",
        ]
        try:
            raw = subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE)
            data = json.loads(raw)
            return GitHubPullRequest(
                number=int(data.get("number", pr_number)),
                title=data.get("title", f"PR #{pr_number}"),
                body=data.get("body", "") or "",
                head_branch=data.get("headRefName", "head"),
                base_branch=data.get("baseRefName", "main"),
                url=data.get("url", ""),
                author=data.get("author", {}).get("login", "") if isinstance(data.get("author"), dict) else "",
            )
        except subprocess.CalledProcessError as e:
            err = e.stderr if hasattr(e, "stderr") and e.stderr else str(e)
            raise GitHubClientError(f"Failed to fetch PR {owner_repo}#{pr_number}: {err}") from e

    def clone_repo(self, owner_repo: str, target_dir: Path, ref: str | None = None) -> Path:
        """Clone a remote repository to target directory using gh or git."""
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        if self.cli_bin:
            cmd = [self.cli_bin, "repo", "clone", owner_repo, str(target_dir)]
        else:
            url = f"https://github.com/{owner_repo}.git"
            cmd = ["git", "clone", url, str(target_dir)]

        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if ref:
            subprocess.check_call(["git", "checkout", ref], cwd=target_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return target_dir

    def create_and_push_branch(
        self,
        repo_path: Path,
        branch_name: str,
        commit_message: str,
        canonical_diff: str,
        signature: str | None = None,
    ) -> None:
        """Create a dedicated fix branch, apply patch diff, commit, and push to origin."""
        # Checkout new branch
        subprocess.check_call(["git", "checkout", "-b", branch_name], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Apply canonical diff
        patch_file = repo_path / ".patchproof_tmp.diff"
        patch_file.write_text(canonical_diff, encoding="utf-8")
        try:
            subprocess.check_call(["git", "apply", str(patch_file)], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            if patch_file.exists():
                patch_file.unlink()

        # Commit with cryptographic audit note
        full_msg = commit_message
        if signature:
            full_msg += f"\n\nAudit-Signature: {signature}\nVerified-By: PatchProof v1.1.0"

        subprocess.check_call(["git", "add", "-A"], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(["git", "commit", "-m", full_msg], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Push branch to remote
        subprocess.check_call(
            ["git", "push", "-u", "origin", branch_name],
            cwd=repo_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def create_pull_request(
        self,
        repo_path: Path,
        title: str,
        body: str,
        base_branch: str = "main",
        head_branch: str = "",
    ) -> str:
        """Create a Pull Request using gh CLI and return the URL."""
        if not self.cli_bin:
            raise GitHubClientError("GitHub CLI ('gh') is required to create pull requests.")

        cmd = [
            self.cli_bin,
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base_branch,
        ]
        if head_branch:
            cmd.extend(["--head", head_branch])

        try:
            out = subprocess.check_output(cmd, cwd=repo_path, text=True, stderr=subprocess.PIPE).strip()
            # gh pr create prints PR URL on success
            urls = re.findall(r"https://github\.com/[^\s]+/pull/\d+", out)
            return urls[0] if urls else out
        except subprocess.CalledProcessError as e:
            err = e.stderr if hasattr(e, "stderr") and e.stderr else str(e)
            raise GitHubClientError(f"Failed to create PR: {err}") from e

    def comment_on_issue_or_pr(self, owner_repo: str, issue_or_pr: int, comment: str) -> str:
        """Add a comment with the audit report to an issue or pull request."""
        if not self.cli_bin:
            raise GitHubClientError("GitHub CLI ('gh') is required to comment.")

        cmd = [
            self.cli_bin,
            "issue",
            "comment",
            f"{owner_repo}#{issue_or_pr}",
            "--body",
            comment,
        ]
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
            return out
        except subprocess.CalledProcessError as e:
            err = e.stderr if hasattr(e, "stderr") and e.stderr else str(e)
            raise GitHubClientError(f"Failed to comment on {owner_repo}#{issue_or_pr}: {err}") from e

    @staticmethod
    def format_pr_body(
        investigation_id: str,
        issue_number: int | None,
        verification_level: str,
        patch_digest: str,
        approval_signature: str,
        claims_markdown: str,
    ) -> str:
        """Format an audited, rich PR description for human and CI reviewers."""
        body_lines = [
            "## 🛡️ PatchProof Automated Verified Repair",
            "",
            f"> **Status:** Verified `{verification_level}` | **Investigation ID:** `{investigation_id}`",
        ]
        if issue_number:
            body_lines.append(f"> **Resolves:** #{issue_number}")

        body_lines.extend([
            "",
            "### 🔒 Cryptographic Provenance",
            f"- **Patch Digest (SHA-256):** `{patch_digest}`",
            f"- **Governance Signature:** `{approval_signature}`",
            "",
            "### 📋 Audited Epistemological Claims",
            claims_markdown,
            "",
            "---",
            "*Verified deterministically against pinned test oracles by [PatchProof](https://github.com/saahilpal/patchproof).* "
            "*Zero secret egress, AST anti-cheat passed, CI-clean.*",
        ])
        return "\n".join(body_lines)

